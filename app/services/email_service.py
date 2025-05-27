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
from app.models import Group, EmailLog
from app.services.token_service import TokenService
from config.settings import Config

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
        self.imap_server = getattr(Config, 'IMAP_SERVER', 'imap.gmail.com')
        self.imap_port = getattr(Config, 'IMAP_PORT', 993)
        self.imap_username = getattr(Config, 'IMAP_USERNAME', Config.SMTP_USERNAME)
        self.imap_password = getattr(Config, 'IMAP_PASSWORD', Config.SMTP_PASSWORD)

        self.token_service = TokenService()

    def check_and_process_emails(self) -> Dict[str, Any]:
        """
        檢查並處理新的轉帳通知郵件

        Returns:
            處理結果統計
        """
        result = {
            'total_emails': 0,
            'processed_emails': 0,
            'successful_matches': 0,
            'failed_matches': 0,
            'errors': []
        }

        try:
            # 連接到 IMAP 伺服器
            with imapclient.IMAPClient(self.imap_server, ssl=True) as client:
                client.login(self.imap_username, self.imap_password)

                # 選擇收件箱
                client.select_folder('INBOX')

                # 搜尋最近24小時內的未讀郵件
                since_date = datetime.now() - timedelta(hours=24)
                messages = client.search(['UNSEEN', 'SINCE', since_date.date()])

                result['total_emails'] = len(messages)
                logger.info(f"找到 {len(messages)} 封新郵件")

                for msg_id in messages:
                    try:
                        # 獲取郵件內容
                        raw_message = client.fetch([msg_id], ['RFC822'])
                        email_message = email.message_from_bytes(raw_message[msg_id][b'RFC822'])

                        # 解析郵件
                        transfer_info = self._parse_transfer_email(email_message)

                        if transfer_info:
                            # 處理轉帳對帳
                            success = self._process_transfer_matching(transfer_info)

                            if success:
                                result['successful_matches'] += 1
                                # 標記郵件為已讀
                                client.set_flags([msg_id], ['\\Seen'])
                            else:
                                result['failed_matches'] += 1

                        result['processed_emails'] += 1

                    except Exception as e:
                        error_msg = f"處理郵件 {msg_id} 時發生錯誤: {str(e)}"
                        logger.error(error_msg)
                        result['errors'].append(error_msg)

        except Exception as e:
            error_msg = f"連接或處理 IMAP 郵件時發生錯誤: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)

        return result

    def _parse_transfer_email(self, email_message) -> Optional[Dict[str, Any]]:
        """
        解析轉帳通知郵件

        Args:
            email_message: 郵件物件

        Returns:
            轉帳資訊字典或None
        """
        try:
            # 取得郵件基本資訊
            subject = email_message['Subject'] or ''
            sender = email_message['From'] or ''
            date_str = email_message['Date'] or ''

            # 取得郵件內容
            body = ''
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == 'text/plain':
                        body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
            else:
                body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')

            # 檢查是否為銀行轉帳通知
            if not self._is_bank_transfer_notification(subject, sender, body):
                return None

            # 解析轉帳資訊
            transfer_info = self._extract_transfer_details(subject, body)

            if transfer_info:
                transfer_info.update({
                    'email_subject': subject,
                    'sender': sender,
                    'email_date': date_str,
                    'email_body': body[:1000]  # 保留前1000字符用於除錯
                })

                logger.info(f"成功解析轉帳郵件: 金額 {transfer_info.get('amount')}, ID {transfer_info.get('transfer_id')}")
                return transfer_info

        except Exception as e:
            logger.error(f"解析轉帳郵件時發生錯誤: {str(e)}")

        return None

    def _is_bank_transfer_notification(self, subject: str, sender: str, body: str) -> bool:
        """
        判斷是否為銀行轉帳通知郵件

        Args:
            subject: 郵件主旨
            sender: 寄件者
            body: 郵件內容

        Returns:
            是否為轉帳通知
        """
        # 銀行轉帳通知的關鍵字
        bank_keywords = [
            '轉帳通知', '入帳通知', '匯款通知', '存款通知',
            'transfer notification', 'deposit notification',
            '台灣銀行', '中國信託', '國泰世華', '玉山銀行', '台新銀行'
        ]

        # 檢查主旨或內容是否包含銀行相關關鍵字
        text_to_check = f"{subject} {body}".lower()

        for keyword in bank_keywords:
            if keyword.lower() in text_to_check:
                return True

        return False

    def _extract_transfer_details(self, subject: str, body: str) -> Optional[Dict[str, Any]]:
        """
        從郵件內容中提取轉帳詳細資訊

        Args:
            subject: 郵件主旨
            body: 郵件內容

        Returns:
            轉帳詳細資訊或None
        """
        try:
            # 合併主旨和內容進行分析
            full_text = f"{subject}\n{body}"

            # 提取金額（支援多種格式）
            amount_patterns = [
                r'金額[：:]\s*NT?\$?\s*([\d,]+)',
                r'存入[：:]\s*NT?\$?\s*([\d,]+)',
                r'轉帳金額[：:]\s*NT?\$?\s*([\d,]+)',
                r'匯款金額[：:]\s*NT?\$?\s*([\d,]+)',
                r'入帳[：:]\s*NT?\$?\s*([\d,]+)',
                r'amount[：:]\s*NT?\$?\s*([\d,]+)',
            ]

            amount = None
            for pattern in amount_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    amount = float(amount_str)
                    break

            if not amount or amount <= 0:
                logger.warning("無法從郵件中提取有效金額")
                return None

            # 提取轉帳唯一識別ID（交易序號、參考號碼等）
            id_patterns = [
                r'交易序號[：:]\s*([A-Z0-9]+)',
                r'參考號碼[：:]\s*([A-Z0-9]+)',
                r'轉帳序號[：:]\s*([A-Z0-9]+)',
                r'transaction\s+id[：:]\s*([A-Z0-9]+)',
                r'reference[：:]\s*([A-Z0-9]+)',
            ]

            transfer_id = None
            for pattern in id_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    transfer_id = match.group(1)
                    break

            # 如果沒有找到明確的交易ID，生成一個基於內容的ID
            if not transfer_id:
                import hashlib
                content_hash = hashlib.md5(full_text.encode()).hexdigest()[:12]
                transfer_id = f"AUTO_{content_hash}"

            # 提取轉帳時間
            time_patterns = [
                r'轉帳時間[：:]\s*(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2})',
                r'交易時間[：:]\s*(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2})',
                r'時間[：:]\s*(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2})',
            ]

            transfer_time = None
            for pattern in time_patterns:
                match = re.search(pattern, full_text)
                if match:
                    try:
                        time_str = match.group(1).replace('/', '-')
                        transfer_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
                    except ValueError:
                        continue
                    break

            if not transfer_time:
                transfer_time = datetime.now()

            return {
                'amount': amount,
                'transfer_id': transfer_id,
                'transfer_time': transfer_time
            }

        except Exception as e:
            logger.error(f"提取轉帳詳細資訊時發生錯誤: {str(e)}")
            return None

    def _process_transfer_matching(self, transfer_info: Dict[str, Any]) -> bool:
        """
        處理轉帳對帳邏輯

        Args:
            transfer_info: 轉帳資訊

        Returns:
            對帳是否成功
        """
        try:
            with get_db_session() as db:
                # 檢查是否已經處理過這筆轉帳
                existing_log = db.query(EmailLog).filter_by(
                    transfer_id=transfer_info['transfer_id']
                ).first()

                if existing_log:
                    logger.warning(f"轉帳ID {transfer_info['transfer_id']} 已經處理過")
                    return False

                # 這裡需要實作識別是哪個群組的轉帳
                # 可能的方法：
                # 1. 從郵件內容中尋找群組識別碼
                # 2. 根據轉帳備註信息
                # 3. 根據金額和時間範圍匹配待處理的購買請求

                target_group = self._identify_target_group(transfer_info)

                if not target_group:
                    # 無法識別目標群組，記錄為待處理
                    email_log = EmailLog(
                        group_id=None,
                        email_subject=transfer_info['email_subject'],
                        sender=transfer_info['sender'],
                        transfer_amount=transfer_info['amount'],
                        transfer_id=transfer_info['transfer_id'],
                        transfer_time=transfer_info['transfer_time'],
                        processing_status='unmatched',
                        error_message='無法識別目標群組'
                    )
                    db.add(email_log)
                    db.commit()

                    logger.warning(f"無法識別轉帳目標群組: {transfer_info['transfer_id']}")
                    return False

                # 建立Email記錄
                email_log = EmailLog(
                    group_id=target_group.id,
                    email_subject=transfer_info['email_subject'],
                    sender=transfer_info['sender'],
                    transfer_amount=transfer_info['amount'],
                    transfer_id=transfer_info['transfer_id'],
                    transfer_time=transfer_info['transfer_time'],
                    processing_status='processing'
                )
                db.add(email_log)
                db.flush()

                # 執行Token充值
                success = self.token_service.add_tokens_from_deposit(
                    line_group_id=target_group.line_group_id,
                    amount=transfer_info['amount'],
                    transfer_id=transfer_info['transfer_id'],
                    description=f"Email自動對帳: {transfer_info['email_subject'][:50]}"
                )

                if success:
                    # 更新處理狀態
                    email_log.processing_status = 'success'
                    email_log.tokens_added = transfer_info['amount']
                    email_log.processed_at = datetime.now()

                    logger.info(f"自動對帳成功: 群組 {target_group.line_group_id}, 金額 {transfer_info['amount']}")

                    # TODO: 發送Line通知給群組
                    # self._send_line_notification(target_group.line_group_id, transfer_info)

                else:
                    # 處理失敗
                    email_log.processing_status = 'failed'
                    email_log.error_message = 'Token充值失敗'

                db.commit()
                return success

        except Exception as e:
            logger.error(f"處理轉帳對帳時發生錯誤: {str(e)}")
            return False

    def _identify_target_group(self, transfer_info: Dict[str, Any]) -> Optional[Group]:
        """
        識別轉帳的目標群組

        Args:
            transfer_info: 轉帳資訊

        Returns:
            目標群組或None
        """
        try:
            with get_db_session() as db:
                # 方法1: 從郵件內容中尋找群組識別碼
                full_text = f"{transfer_info.get('email_subject', '')} {transfer_info.get('email_body', '')}"

                # 尋找群組ID模式 (例如: GROUP_xxxxx)
                group_id_match = re.search(r'GROUP_([A-Z0-9]+)', full_text, re.IGNORECASE)
                if group_id_match:
                    group_identifier = group_id_match.group(1)
                    group = db.query(Group).filter(
                        Group.line_group_id.like(f'%{group_identifier}%')
                    ).first()
                    if group:
                        return group

                # 方法2: 暫時返回第一個活躍群組（這需要根據實際業務邏輯調整）
                # 在實際應用中，您可能需要更複雜的邏輯來匹配群組
                groups = db.query(Group).filter_by(is_active=True).all()

                if len(groups) == 1:
                    # 如果只有一個群組，直接返回
                    return groups[0]

                # TODO: 實作更複雜的匹配邏輯
                # 例如: 根據轉帳金額、時間等信息匹配待處理的購買請求

                return None

        except Exception as e:
            logger.error(f"識別目標群組時發生錯誤: {str(e)}")
            return None

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
