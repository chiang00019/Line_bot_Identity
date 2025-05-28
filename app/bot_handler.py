# app/bot_handler.py (恢復資料庫操作版)
from linebot.models import TextSendMessage
import logging
from sqlalchemy.exc import IntegrityError

# 從 .database 導入 get_db_session，從 .models 導入所有需要的模型
from .database import get_db_session
from .models import Group, User, GroupMember, TokenLog # 確保 Base 在 models.py 被正確定義和使用

logger = logging.getLogger("app.bot_handler")

class BotCommandHandler:
    def __init__(self, line_bot_api):
        self.line_bot_api = line_bot_api

    def _get_user_display_name(self, user_id):
        """嘗試獲取用戶的顯示名稱"""
        try:
            profile = self.line_bot_api.get_profile(user_id)
            return profile.display_name
        except Exception as e:
            logger.warning(f"Failed to get profile for user {user_id}: {e}")
            return f"用戶_{user_id[-6:]}" # 返回一個預設名稱

    def _handle_bind_token(self, event):
        user_id = event.source.user_id
        group_id = event.source.group_id

        logger.info(f"Group {group_id}: Received /綁定Token command from user {user_id}")
        reply_text = ""

        try:
            with get_db_session() as db:
                # 檢查群組是否已經綁定
                existing_group = db.query(Group).filter(Group.line_group_id == group_id).first()
                if existing_group:
                    reply_text = f"⚠️ 本群組 (ID: ...{group_id[-6:]}) 已經綁定過 Token 帳戶了！\n目前餘額: {existing_group.token_balance} Token"
                    self.line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
                    return

                # 嘗試獲取群組名稱 (如果 Line API 支援且 Bot 在群組內有權限)
                # group_summary = self.line_bot_api.get_group_summary(group_id)
                # group_name = group_summary.group_name
                # 暫時使用預設名稱
                group_name = f"群組_{group_id[-6:]}"

                # 建立新群組
                new_group = Group(
                    line_group_id=group_id,
                    group_name=group_name, # 你可能需要從 Line API 獲取真實群組名
                    token_balance=0.0,
                    is_active=True
                )
                db.add(new_group)
                db.flush() # 需要 group.id 以便關聯 GroupMember

                # 檢查用戶是否存在，不存在則建立
                user = db.query(User).filter(User.line_user_id == user_id).first()
                if not user:
                    user_display_name = self._get_user_display_name(user_id)
                    user = User(line_user_id=user_id, display_name=user_display_name)
                    db.add(user)
                    db.flush() # 需要 user.id

                # 設定發起綁定的用戶為管理員
                new_member = GroupMember(group_id=new_group.id, user_id=user.id, is_admin=True)
                db.add(new_member)

                db.commit()
                reply_text = (
                    f"✅ 本群組 (ID: ...{group_id[-6:]}) 已成功綁定 Token 帳戶！\n"
                    f"👑 {user.display_name} 已被設為首位管理員。\n"
                    f"💰 目前 Token 餘額: {new_group.token_balance}。"
                )
                logger.info(f"Group {group_id} successfully bound by user {user_id}. New group ID: {new_group.id}")

        except IntegrityError as e: # 處理可能的唯一性約束衝突，例如重複綁定
            db.rollback()
            logger.error(f"IntegrityError during binding group {group_id}: {e}")
            reply_text = f"⚠️ 綁定失敗，群組可能已經存在或資料庫發生衝突。請稍後再試。"
        except Exception as e:
            db.rollback()
            logger.error(f"Error binding group {group_id} for user {user_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            reply_text = "❌ 綁定 Token 時發生未預期的錯誤，請聯繫管理員。"

        self.line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

    def _handle_query_token(self, event):
        group_id = event.source.group_id
        user_id = event.source.user_id
        logger.info(f"Group {group_id}: Received /查詢Token command from user {user_id}")
        reply_text = ""

        try:
            with get_db_session() as db:
                group = db.query(Group).filter(Group.line_group_id == group_id).first()
                if not group:
                    reply_text = f"⚠️ 本群組 (ID: ...{group_id[-6:]}) 尚未綁定 Token 帳戶。\n請管理員使用 `/綁定Token` 指令。"
                else:
                    # 之後可以加入顯示交易歷史
                    reply_text = (
                        f"💰 群組 '{group.group_name}' Token 資訊：\n"
                        f"💳 目前餘額: {group.token_balance:.1f} Token。"
                    )
        except Exception as e:
            logger.error(f"Error querying token for group {group_id}: {e}")
            reply_text = "❌ 查詢 Token 時發生錯誤。"

        self.line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))


    def handle_command(self, event):
        user_id = event.source.user_id
        message_text = event.message.text.strip().lower()
        is_group = hasattr(event.source, 'group_id')
        group_id = event.source.group_id if is_group else "N/A"

        logger.info(f"Received message: '{message_text}' from user: {user_id} in {'group: ' + group_id if is_group else 'private chat'}")
        reply_text = None

        if message_text in ['hello', 'hi', '你好', '哈囉']:
            reply_text = f"👋 您好 {self._get_user_display_name(user_id)}！很高興為您服務。"
        elif message_text in ['開始', 'start']:
            reply_text = "🚀 歡迎使用！輸入 /說明 查看可用指令。"
        elif message_text == '/說明' or message_text == '/help':
            base_commands = (
                "🤖 Line Bot 功能說明 (v0.2)\n\n"
                "--- 基本指令 ---\n"
                "• Hello / 你好 - 基本問候\n"
                "• 開始 / start - 顯示開始訊息\n"
                "• /說明 (/help) - 顯示此說明\n\n"
                "--- 群組專用指令 ---\n"
                "• /綁定Token - (群組)開始綁定Token帳戶流程\n"
                "• /查詢Token - (群組)查詢目前Token餘額\n"
            )
            reply_text = base_commands + "\n\n🔧 更多功能陸續推出！"

        elif is_group:
            if message_text == '/綁定token':
                self._handle_bind_token(event)
                return # _handle_bind_token 內部已回覆
            elif message_text == '/查詢token':
                self._handle_query_token(event)
                return # _handle_query_token 內部已回覆
            else:
                pass # 群組中未知指令不回應
        else: # 私人訊息
            if message_text.startswith('/'):
                reply_text = "ℹ️ 此指令需要在群組中使用喔！"
            else:
                reply_text = f"📝 您說：{event.message.text}\n請輸入 /說明 查看可用指令。"

        if reply_text:
            self.line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
            logger.info(f"Replied to {user_id} with: \"{reply_text[:50]}...\"")
        # else:
            # logger.info(f"No standard reply sent for message: '{message_text}' from {user_id} in {'group ' + group_id if is_group else 'private chat'}")


def handle_message(line_bot_api, event):
    try:
        if event.type == "message" and event.message.type == "text":
            command_handler = BotCommandHandler(line_bot_api)
            command_handler.handle_command(event)
        elif event.type == "join":
            group_id = event.source.group_id
            logger.info(f"Bot joined group: {group_id}")
            reply_text = "🎉 大家好！Token 管理 Bot 已加入群組！請管理員使用 `/綁定Token` 指令來啟用服務。"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        # 可以後續加入處理其他事件類型

    except Exception as e:
        logger.error(f"Error in global handle_message: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="喔喔，Bot 處理您的訊息時有點小問題，請稍後再試或聯繫管理員 😥")
            )
        except Exception as e2:
            logger.error(f"Failed to send error reply: {str(e2)}")
