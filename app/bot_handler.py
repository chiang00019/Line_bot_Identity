# -*- coding: utf-8 -*-
"""
Line Bot 訊息處理邏輯 - 支援群組共享Token管理
"""

from linebot.models import TextSendMessage, QuickReply, QuickReplyButton, MessageAction
from app.database import get_db_session
from app.models import Group, User, GroupMember, TokenLog
from app.services.token_service import TokenService
from app.services.email_service import EmailService
from app.services.razer_service import RazerService
import logging
import re

logger = logging.getLogger(__name__)

class BotHandler:
    """Line Bot 訊息處理器"""

    def __init__(self):
        self.token_service = TokenService()
        self.email_service = EmailService()
        self.razer_service = RazerService()

    def handle_message(self, line_bot_api, event):
        """
        處理來自Line Bot的訊息

        Args:
            line_bot_api: Line Bot API 實例
            event: Line Bot 事件物件
        """
        try:
            user_id = event.source.user_id
            message_text = event.message.text.strip()

            # 檢查是否來自群組
            if hasattr(event.source, 'group_id'):
                group_id = event.source.group_id
                reply_message = self._handle_group_message(user_id, group_id, message_text)
            else:
                # 私人訊息
                reply_message = self._handle_private_message(user_id, message_text)

            # 回覆訊息
            line_bot_api.reply_message(event.reply_token, reply_message)

        except Exception as e:
            logger.error(f"處理訊息時發生錯誤: {str(e)}")
            error_message = TextSendMessage(text="❌ 系統發生錯誤，請稍後再試。")
            line_bot_api.reply_message(event.reply_token, error_message)

    def _handle_group_message(self, user_id: str, group_id: str, message_text: str):
        """處理群組訊息"""

        # 指令解析
        if message_text == "/綁定Token":
            return self._handle_bind_token(user_id, group_id)

        elif message_text == "/購買Token":
            return self._handle_buy_token_info(group_id)

        elif message_text == "/查詢Token":
            return self._handle_query_token(group_id)

        elif message_text.startswith("/儲值"):
            return self._handle_recharge_command(user_id, group_id, message_text)

        elif message_text.startswith("/設置管理員"):
            return self._handle_set_admin(user_id, group_id, message_text)

        elif message_text.startswith("/刪除管理員"):
            return self._handle_remove_admin(user_id, group_id, message_text)

        elif message_text.startswith("/更新Token"):
            return self._handle_manual_update_token(user_id, group_id, message_text)

        elif message_text == "/刪除綁定":
            return self._handle_unbind_token(user_id, group_id)

        elif message_text == "/說明" or message_text == "/help":
            return self._create_help_message()

        else:
            # 非指令訊息，不回應
            return None

    def _handle_private_message(self, user_id: str, message_text: str):
        """處理私人訊息"""
        return TextSendMessage(
            text="👋 您好！請將我加入群組中使用，我是群組共享Token管理Bot。\n\n"
                 "使用方式：\n"
                 "1. 將我邀請到您的群組\n"
                 "2. 在群組中輸入 /綁定Token 開始使用\n"
                 "3. 輸入 /說明 查看所有指令"
        )

    def _handle_bind_token(self, user_id: str, group_id: str):
        """處理綁定Token指令"""
        try:
            with get_db_session() as db:
                # 檢查群組是否已經綁定
                existing_group = db.query(Group).filter_by(line_group_id=group_id).first()
                if existing_group:
                    return TextSendMessage(text="⚠️ 本群組已經綁定過Token帳戶了！")

                # 建立新群組
                new_group = Group(
                    line_group_id=group_id,
                    group_name=f"群組_{group_id[:8]}",
                    token_balance=0.0,
                    is_active=True
                )
                db.add(new_group)
                db.flush()  # 取得 group.id

                # 建立用戶（如果不存在）
                user = db.query(User).filter_by(line_user_id=user_id).first()
                if not user:
                    user = User(line_user_id=user_id, display_name="用戶")
                    db.add(user)
                    db.flush()

                # 建立群組成員關係，第一個操作者自動成為管理員
                group_member = GroupMember(
                    group_id=new_group.id,
                    user_id=user.id,
                    is_admin=True
                )
                db.add(group_member)

                db.commit()

                return TextSendMessage(
                    text="✅ 本群組已成功綁定Token帳戶！\n\n"
                         f"👑 您已被設為群組管理員\n"
                         f"💰 目前Token餘額：0\n\n"
                         f"接下來您可以：\n"
                         f"• /購買Token - 查看充值資訊\n"
                         f"• /查詢Token - 查看餘額與記錄\n"
                         f"• /儲值 [金額] [帳號] - 進行Razer儲值\n"
                         f"• /說明 - 查看所有指令"
                )

        except Exception as e:
            logger.error(f"綁定Token失敗: {str(e)}")
            return TextSendMessage(text="❌ 綁定Token失敗，請稍後再試。")

    def _handle_buy_token_info(self, group_id: str):
        """處理購買Token資訊查詢"""
        try:
            with get_db_session() as db:
                group = db.query(Group).filter_by(line_group_id=group_id).first()
                if not group:
                    return TextSendMessage(text="⚠️ 本群組尚未綁定Token帳戶，請先使用 /綁定Token")

                # 從系統配置中取得銀行資訊
                from app.models import SystemConfig
                bank_info = db.query(SystemConfig).filter_by(config_key='bank_account_info').first()
                min_amount = db.query(SystemConfig).filter_by(config_key='min_deposit_amount').first()

                bank_text = bank_info.config_value if bank_info else "請聯繫管理員取得轉帳資訊"
                min_text = min_amount.config_value if min_amount else "100"

                return TextSendMessage(
                    text="💳 Token充值資訊\n\n"
                         f"💰 兌換比率：1 NT$ = 1 Token\n"
                         f"💵 最低充值：NT$ {min_text}\n\n"
                         f"🏦 轉帳資訊：\n{bank_text}\n\n"
                         f"📧 轉帳後系統將自動Email對帳\n"
                         f"✅ 確認後Token會自動加入群組餘額\n\n"
                         f"💡 提醒：轉帳時請備註群組識別碼以便對帳"
                )

        except Exception as e:
            logger.error(f"查詢購買Token資訊失敗: {str(e)}")
            return TextSendMessage(text="❌ 查詢購買資訊失敗，請稍後再試。")

    def _handle_query_token(self, group_id: str):
        """處理查詢Token指令"""
        try:
            with get_db_session() as db:
                group = db.query(Group).filter_by(line_group_id=group_id).first()
                if not group:
                    return TextSendMessage(text="⚠️ 本群組尚未綁定Token帳戶，請先使用 /綁定Token")

                # 查詢最近的交易記錄
                recent_logs = db.query(TokenLog).filter_by(group_id=group.id)\
                              .order_by(TokenLog.created_at.desc()).limit(5).all()

                response_text = f"💰 群組Token資訊\n\n"
                response_text += f"💳 目前餘額：{group.token_balance:.1f} Token\n\n"

                if recent_logs:
                    response_text += "📊 最近交易記錄：\n"
                    for log in recent_logs:
                        type_emoji = "⬆️" if log.transaction_type in ['deposit', 'manual_add'] else "⬇️"
                        response_text += f"{type_emoji} {log.created_at.strftime('%m/%d %H:%M')} "
                        response_text += f"{log.transaction_type} {log.amount:+.1f}\n"
                else:
                    response_text += "📊 暫無交易記錄\n"

                response_text += f"\n💡 使用 /購買Token 查看充值方式"

                return TextSendMessage(text=response_text)

        except Exception as e:
            logger.error(f"查詢Token失敗: {str(e)}")
            return TextSendMessage(text="❌ 查詢Token失敗，請稍後再試。")

    def _handle_recharge_command(self, user_id: str, group_id: str, message_text: str):
        """處理儲值指令"""
        try:
            # 解析指令格式：/儲值 [金額] [帳號]
            parts = message_text.split()
            if len(parts) != 3:
                return TextSendMessage(
                    text="❌ 指令格式錯誤\n\n"
                         "正確格式：/儲值 [金額] [帳號]\n"
                         "範例：/儲值 500 user123"
                )

            try:
                amount = float(parts[1])
                account = parts[2]
            except ValueError:
                return TextSendMessage(text="❌ 金額格式錯誤，請輸入數字")

            if amount <= 0:
                return TextSendMessage(text="❌ 金額必須大於0")

            # 檢查群組和用戶權限
            with get_db_session() as db:
                group = db.query(Group).filter_by(line_group_id=group_id).first()
                if not group:
                    return TextSendMessage(text="⚠️ 本群組尚未綁定Token帳戶")

                # 檢查Token餘額是否足夠
                if group.token_balance < amount:
                    return TextSendMessage(
                        text=f"❌ Token餘額不足\n\n"
                             f"目前餘額：{group.token_balance:.1f} Token\n"
                             f"需要金額：{amount:.1f} Token\n"
                             f"請先使用 /購買Token 充值"
                    )

                # 開始異步儲值流程
                success = self.razer_service.start_recharge_process(
                    group_id=group.id,
                    user_id=user_id,
                    amount=amount,
                    account=account
                )

                if success:
                    return TextSendMessage(
                        text=f"🚀 儲值流程已開始！\n\n"
                             f"💰 儲值金額：NT$ {amount}\n"
                             f"🎮 目標帳號：{account}\n"
                             f"⏳ 預計完成時間：2-5分鐘\n\n"
                             f"📱 完成後將自動回傳ZIP憑證檔案\n"
                             f"💳 Token已先行扣除 {amount:.1f} 點"
                    )
                else:
                    return TextSendMessage(text="❌ 儲值流程啟動失敗，請稍後再試")

        except Exception as e:
            logger.error(f"處理儲值指令失敗: {str(e)}")
            return TextSendMessage(text="❌ 儲值指令處理失敗，請稍後再試。")

    def _check_admin_permission(self, user_id: str, group_id: str) -> bool:
        """檢查用戶是否為群組管理員"""
        try:
            with get_db_session() as db:
                group = db.query(Group).filter_by(line_group_id=group_id).first()
                if not group:
                    return False

                user = db.query(User).filter_by(line_user_id=user_id).first()
                if not user:
                    return False

                member = db.query(GroupMember).filter_by(
                    group_id=group.id, user_id=user.id, is_admin=True
                ).first()

                return member is not None
        except Exception:
            return False

    def _create_help_message(self):
        """建立說明訊息"""
        help_text = """
🤖 Line Bot Token管理系統

📋 可用指令：
/綁定Token - 綁定群組Token帳戶
/購買Token - 查看Token充值資訊
/查詢Token - 查看餘額與交易記錄
/儲值 [金額] [帳號] - 自動Razer儲值
/設置管理員 @用戶 - 設定群組管理員
/刪除管理員 @用戶 - 移除群組管理員
/更新Token [編號] - 手動補登Token
/刪除綁定 - 解除群組綁定(管理員)
/說明 - 顯示此說明

🔧 功能特色：
• 群組共享Token管理
• Email自動對帳充值
• Razer全自動儲值
• 憑證自動截圖ZIP
• 多管理員權限控制

❓ 如有問題請聯繫系統管理員
        """

        return TextSendMessage(text=help_text.strip())

# 建立全域處理器實例
bot_handler = BotHandler()

def handle_message(line_bot_api, event):
    """全域訊息處理函數（向後兼容）"""
    return bot_handler.handle_message(line_bot_api, event)
