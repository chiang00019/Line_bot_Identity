# -*- coding: utf-8 -*-
"""
Email 服務 - 處理 IMAP 郵件爬取與自動對帳
"""

import aiosmtplib
import imapclient
import email
import logging
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.database import get_db_session
from app.models import Group, EmailLog, TokenLog, SystemConfig
from app.services.token_service import TokenService
from config.settings import Config
from email.header import decode_header

logger = logging.getLogger(__name__)

class EmailService:
    """Email 服務類別 - 支援 IMAP 爬取與自動對帳"""

    def __init__(self):
        """初始化 Email 服務"""
        # SMTP 設定（發送郵件）
        self.smtp_server = Config.SMTP_SERVER
        self.smtp_port = Config.SMTP_PORT
        self.smtp_username = Config.SMTP_USERNAME
        self.smtp_password = Config.SMTP_PASSWORD
        self.from_email = Config.FROM_EMAIL

        # IMAP 設定（接收郵件）
        self.imap_host = Config.IMAP_HOST
        self.imap_port = int(Config.IMAP_PORT) if Config.IMAP_PORT else 993
        self.imap_username = Config.IMAP_USERNAME
        self.imap_password = Config.IMAP_PASSWORD

        self.token_service = TokenService()

        logger.info(f"EmailService initialized. IMAP Host: {self.imap_host}, Port: {self.imap_port}, User configured: {bool(self.imap_username)}")

    def _decode_mail_header(self, header_value: str) -> str:
        if not header_value:
            return ""
        try:
            decoded_parts = []
            for part, charset in decode_header(header_value):
                if isinstance(part, bytes):
                    decoded_parts.append(part.decode(charset or 'utf-8', errors='replace'))
                else:
                    decoded_parts.append(part)
            return "".join(decoded_parts)
        except Exception as e:
            logger.warning(f"Failed to decode header '{str(header_value)[:50]}...': {e}")
            if isinstance(header_value, bytes):
                 try: return header_value.decode('utf-8', errors='replace')
                 except: pass
            return str(header_value) # fallback

    def check_and_process_emails(self) -> Dict[str, Any]:
        logger.info("Starting email check and processing...")
        if not all([self.imap_host, self.imap_username, self.imap_password]):
            logger.warning("IMAP settings (host, username, or password) are not fully configured. Skipping email check.")
            return {"status": "skipped", "reason": "IMAP not configured"}

        processed_summary = {
            "emails_fetched": 0, "transfers_parsed": 0,
            "tokens_added_count": 0, "errors": [], "already_processed": 0
        }

        try:
            with imapclient.IMAPClient(self.imap_host, port=self.imap_port, ssl=True) as client:
                logger.info(f"Connecting to IMAP server: {self.imap_host}")
                client.login(self.imap_username, self.imap_password)
                logger.info("IMAP login successful.")
                client.select_folder('INBOX')

                search_criteria = ['UNSEEN']
                messages_ids = client.search(search_criteria)
                logger.info(f"Found {len(messages_ids)} email(s) matching criteria: {search_criteria}")
                processed_summary["emails_fetched"] = len(messages_ids)

                for msg_id in messages_ids:
                    try:
                        raw_message = client.fetch([msg_id], ['RFC822', 'INTERNALDATE'])
                        email_message = email.message_from_bytes(raw_message[msg_id][b'RFC822'])
                        internal_date = raw_message[msg_id].get(b'INTERNALDATE', datetime.now())

                        parsed_info = self._parse_transfer_email(email_message, internal_date)
                        if parsed_info:
                            logger.info(f"Parsed transfer info from email UID {msg_id}: {parsed_info}")

                            processed_summary["transfers_parsed"] += 1
                            success, was_duplicate = self._process_parsed_transfer(parsed_info, msg_id)
                            if was_duplicate:
                                processed_summary["already_processed"] += 1
                                client.set_flags([msg_id], [imapclient.SEEN]) # 重複的也標記已讀
                                logger.info(f"Email UID {msg_id} (duplicate transfer_id {parsed_info['transfer_id']}) marked as SEEN.")
                            elif success:
                                processed_summary["tokens_added_count"] += 1
                                client.set_flags([msg_id], [imapclient.SEEN])
                                logger.info(f"Successfully processed email UID {msg_id} and marked as SEEN.")
                            else:
                                logger.warning(f"Failed to process parsed transfer from email UID {msg_id}. It will remain UNSEEN for retry (unless error logged it).")
                        else:
                            logger.info(f"Email UID {msg_id} did not parse as a relevant transfer. Marking as SEEN to avoid re-processing.")
                            client.set_flags([msg_id], [imapclient.SEEN])
                    except Exception as e_msg_proc:
                        logger.error(f"Error processing email UID {msg_id}: {e_msg_proc}")
                        processed_summary["errors"].append(f"Email UID {msg_id}: {str(e_msg_proc)}")

        except imapclient.exceptions.LoginError as e_login:
            logger.error(f"IMAP Login failed: {e_login}")
            processed_summary["errors"].append(f"IMAP LoginError: {str(e_login)}")
        except Exception as e_imap:
            logger.error(f"Error during IMAP operations: {e_imap}")
            import traceback
            logger.error(traceback.format_exc())
            processed_summary["errors"].append(f"IMAP General Error: {str(e_imap)}")

        logger.info(f"Email check and processing finished. Summary: {processed_summary}")
        return processed_summary

    def _parse_transfer_email(self, email_message: email.message.Message, internal_date: Optional[datetime]) -> Optional[Dict[str, Any]]:
        try:
            subject = self._decode_mail_header(email_message.get('Subject', ''))
            sender = self._decode_mail_header(email_message.get('From', ''))
            message_date = internal_date or email.utils.parsedate_to_datetime(email_message.get('Date')) or datetime.now()

            body = ""
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    if content_type == 'text/plain' and 'attachment' not in content_disposition:
                        try:
                            charset = part.get_content_charset() or 'utf-8'
                            body += part.get_payload(decode=True).decode(charset, errors='replace')
                            break
                        except Exception as e_part:
                            logger.warning(f"Could not decode part with charset {part.get_content_charset()}: {e_part}")
            else:
                try:
                    charset = email_message.get_content_charset() or 'utf-8'
                    body = email_message.get_payload(decode=True).decode(charset, errors='replace')
                except Exception as e_payload:
                    logger.warning(f"Could not decode payload with charset {email_message.get_content_charset()}: {e_payload}")

            if not body:
                logger.debug(f"Email from {sender} with subject '{subject}' has empty/unparseable text body.")
                return None

            logger.debug(f"Processing email from: {sender}, Subject: {subject}, Date: {message_date}, Body (first 300 chars):\n{body[:300]}")

            # --- 示例解析逻辑 (你需要根据你的银行邮件格式调整) ---
            # 1. 金额
            amount_match = re.search(r"(?:轉帳|存入|金額)[：:NT\$ ]*([,\d]+\.?\d*)", body, re.IGNORECASE)
            amount = float(amount_match.group(1).replace(",", "")) if amount_match else None
            if not amount:
                 logger.debug(f"No amount found in email: {subject}")
                 return None # 没有金额就不是有效转账通知

            # 2. 交易ID (非常重要，用于防重)
            # 优先使用银行提供的明确交易ID
            bank_tx_id_match = re.search(r"(?:交易序號|參考編號|交易參考碼|Transaction No\.)[：: ]*([a-zA-Z0-9-]+)", body, re.IGNORECASE)
            bank_transaction_id = bank_tx_id_match.group(1) if bank_tx_id_match else None
            if not bank_transaction_id: # 如果没有，尝试从主旨找，或生成一个基于邮件的唯一ID
                bank_tx_id_match_subj = re.search(r"(?:交易序號|參考編號)[：: ]*([a-zA-Z0-9-]+)", subject, re.IGNORECASE)
                bank_transaction_id = bank_tx_id_match_subj.group(1) if bank_tx_id_match_subj else f"email_{email_message.get('Message-ID', str(hash(body+subject)))[-20:]}"

            # 3. 群组标识符 (从邮件备注中提取)
            group_id_fragment_match = re.search(r"(?:備註|摘要|附言|留言|备注)[：: ]*(?:.*)(GROUP_[a-zA-Z0-9_-]+|[GCU][0-9a-f]{6,})", body, re.IGNORECASE | re.DOTALL)
            group_identifier = group_id_fragment_match.group(1) if group_id_fragment_match else None
            if not group_identifier:
                 group_id_fragment_match_subj = re.search(r"(GROUP_[a-zA-Z0-9_-]+|[GCU][0-9a-f]{6,})", subject, re.IGNORECASE) # 也从主旨找
                 group_identifier = group_id_fragment_match_subj.group(1) if group_id_fragment_match_subj else None

            if not group_identifier:
                logger.info(f"No group identifier (e.g., GROUP_XXXX or Cxxxxxx) found in email from {sender} - {subject}.")
                return None

            target_line_group_id = self._find_group_by_identifier(group_identifier)
            if not target_line_group_id:
                logger.warning(f"Could not find active group for identifier: {group_identifier} in email from {sender} - {subject}")
                return None

            # 4. 付款人信息 (可选)
            payer_info_match = re.search(r"(?:從帳號|付款人帳號|From Account)[：: ]*(?:[ \*\d]+)(\d{4,6})", body) # 末4-6碼
            payer_info = payer_info_match.group(1) if payer_info_match else "未知付款人"

            parsed_data = {
                "email_subject": subject, "sender": sender, "transfer_amount": amount,
                "transfer_id": bank_transaction_id, "transfer_time": message_date,
                "target_line_group_id": target_line_group_id, "payer_info": payer_info,
                "raw_email_body": body
            }
            return parsed_data
        except Exception as e:
            logger.error(f"Error parsing email content: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _find_group_by_identifier(self, identifier: str) -> Optional[str]:
        logger.debug(f"Attempting to find group by identifier: {identifier}")
        try:
            with get_db_session() as db:
                group_query = db.query(Group).filter(Group.is_active == True)
                if identifier.upper().startswith("GROUP_"):
                    # 假设 GROUP_xxxxxx 中的 xxxxxx 是 line_group_id 的一部分或完整ID
                    potential_id = identifier[len("GROUP_"):]
                    group = group_query.filter(Group.line_group_id.ilike(f"%{potential_id}%")).first()
                elif re.match(r"^[GCU][0-9a-fA-F]{6,}$", identifier): # C/G/U 开头的 Line ID
                    group = group_query.filter(Group.line_group_id == identifier).first()
                else: # 尝试作为 group_name 或 id 的部分匹配
                    group = group_query.filter( (Group.group_name.ilike(f"%{identifier}%")) | (Group.line_group_id.ilike(f"%{identifier}%")) ).first()

                if group:
                    logger.info(f"Found group {group.line_group_id} for identifier '{identifier}'")
                    return group.line_group_id
            logger.warning(f"No active group found for identifier: {identifier}")
            return None
        except Exception as e:
            logger.error(f"Error in _find_group_by_identifier for '{identifier}': {e}")
            return None

    def _process_parsed_transfer(self, transfer_info: Dict[str, Any], email_uid: Any) -> tuple[bool, bool]: # Returns (success, was_duplicate)
        was_duplicate = False
        try:
            with get_db_session() as db:
                existing_log = db.query(EmailLog).filter(EmailLog.transfer_id == transfer_info["transfer_id"]).first()
                if existing_log:
                    logger.warning(f"Transfer ID {transfer_info['transfer_id']} already processed (EmailLog ID: {existing_log.id}). Skipping token addition.")
                    was_duplicate = True
                    return True, was_duplicate # 成功處理（因為是重複的，不需要再做）

                target_group_obj = db.query(Group).filter(Group.line_group_id == transfer_info["target_line_group_id"]).first()
                if not target_group_obj:
                    logger.error(f"Target group {transfer_info['target_line_group_id']} not found in DB for transfer ID {transfer_info['transfer_id']}.")
                    return False, was_duplicate

                email_log = EmailLog(
                    group_id=target_group_obj.id, email_subject=transfer_info["email_subject"],
                    sender=transfer_info["sender"], transfer_amount=transfer_info["transfer_amount"],
                    transfer_id=transfer_info["transfer_id"], transfer_time=transfer_info["transfer_time"],
                    processing_status="pending", raw_body=transfer_info["raw_email_body"] # 假設 EmailLog 有 raw_body 欄位
                )
                db.add(email_log)
                db.flush()

                token_rate_setting = db.query(SystemConfig).filter(SystemConfig.config_key == 'token_exchange_rate').first()
                token_rate = float(token_rate_setting.config_value) if token_rate_setting and token_rate_setting.config_value else 1.0
                tokens_to_add = transfer_info["transfer_amount"] * token_rate
                description = f"Email自動對帳 ({transfer_info['payer_info']}) - {transfer_info['email_subject'][:30]}"

                # 使用 TokenService 更新 Token，並傳遞 db session 以確保事務一致性
                token_added_successfully = self.token_service.add_tokens_from_deposit(
                    line_group_id=target_group_obj.line_group_id,
                    amount=tokens_to_add,
                    transfer_id=transfer_info["transfer_id"],
                    description=description,
                    db_session=db # 傳遞當前的 session
                )

                if token_added_successfully:
                    email_log.processing_status = "success"
                    email_log.tokens_added = tokens_to_add
                    email_log.processed_at = datetime.now()
                    # db.commit() 由外層的 with get_db_session() 處理
                    logger.info(f"Successfully added {tokens_to_add} tokens to group {target_group_obj.line_group_id} for transfer ID {transfer_info['transfer_id']}.")
                    # TODO: 發送 Line 通知給群組
                    return True, was_duplicate
                else:
                    email_log.processing_status = "failed"
                    email_log.error_message = "TokenService failed to add tokens or duplicate reference_id in TokenLog."
                    # db.commit()
                    logger.error(f"Failed to add tokens for transfer ID {transfer_info['transfer_id']} via TokenService.")
                    return False, was_duplicate
        except Exception as e:
            logger.error(f"Error in _process_parsed_transfer for transfer ID {transfer_info.get('transfer_id', 'N/A')}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 嘗試記錄錯誤到 EmailLog
            try:
                with get_db_session() as db_err: # 使用新的 session 以防外部 session 已損壞
                    err_log = db_err.query(EmailLog).filter(EmailLog.transfer_id == transfer_info["transfer_id"]).first()
                    if err_log and err_log.processing_status == "pending": # 只更新還未確定狀態的
                        err_log.processing_status = "error"
                        err_log.error_message = str(e)[:499] # 截斷
                        db_err.commit()
            except Exception as e_db_log:
                logger.error(f"Failed to log error state for transfer {transfer_info.get('transfer_id', 'N/A')} in EmailLog: {e_db_log}")
            return False, was_duplicate

    async def send_notification_email(self, to_emails: List[str], subject: str, body: str) -> bool:
        """
        發送通知郵件

        Args:
            to_emails: 收件人列表
            subject: 主旨
            body: 內容

        Returns:
            是否發送成功
        """
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            await aiosmtplib.send(
                msg,
                hostname=self.smtp_server,
                port=self.smtp_port,
                start_tls=True,
                username=self.smtp_username,
                password=self.smtp_password,
            )

            logger.info(f"通知郵件發送成功: {subject}")
            return True

        except Exception as e:
            logger.error(f"發送通知郵件時發生錯誤: {str(e)}")
            return False
