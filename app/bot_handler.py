# app/bot_handler.py (恢復基礎功能版)
from linebot.models import TextSendMessage
import logging

logger = logging.getLogger("app.bot_handler")

class BotCommandHandler:
    def __init__(self, line_bot_api):
        self.line_bot_api = line_bot_api

    def handle_command(self, event):
        user_id = event.source.user_id
        message_text = event.message.text.strip().lower()
        reply_text = None
        is_group = hasattr(event.source, 'group_id')
        group_id = event.source.group_id if is_group else None

        logger.info(f"Received message: '{message_text}' from user: {user_id} in {'group: ' + group_id if is_group else 'private chat'}")

        if message_text in ['hello', 'hi', '你好', '哈囉']:
            reply_text = f"👋 您好 {user_id}！很高興為您服務。"
        elif message_text in ['開始', 'start']:
            reply_text = "🚀 歡迎使用！輸入 /說明 查看可用指令。"
        elif message_text == '/說明' or message_text == '/help':
            base_commands = (
                "🤖 Line Bot 功能說明 (基礎版)\n\n"
                "--- 基本指令 ---\n"
                "• Hello / 你好 - 基本問候\n"
                "• 開始 / start - 顯示開始訊息\n"
                "• /說明 (/help) - 顯示此說明\n\n"
                "--- 群組專用指令 ---\n"
                "• /綁定Token - (群組)開始綁定Token帳戶流程\n"
                "• /查詢Token - (群組)查詢目前Token餘額\n"
                # "• /購買Token - (群組)顯示購買Token資訊\n" # 暫時不加回來
                # "• /儲值 金額 帳號 - (群組)進行Razer儲值\n" # 暫時不加回來
            )
            # admin_commands = (
            #     "\n--- 管理員專用 ---\n"
            #     "• /設置管理員 @用戶 - 新增管理員\n"
            #     "• /刪除管理員 @用戶 - 移除管理員\n"
            #     "• /更新Token 編號 - 手動更新Token\n"
            #     "• /刪除綁定 - 解除群組綁定"
            # )
            reply_text = base_commands # + (admin_commands if self._is_admin(user_id, group_id) else "")
            reply_text += "\n\n🔧 更多功能陸續推出！"

        elif is_group: # 以下為群組指令
            if message_text == '/綁定token':
                # TODO: 實際的資料庫綁定邏輯
                reply_text = f"✅ 群組 {group_id} 收到 /綁定Token 指令！\n將開始為此群組建立 Token 帳戶 (目前為模擬)。"
                logger.info(f"Group {group_id}: /綁定Token command received from user {user_id}.")
            elif message_text == '/查詢token':
                # TODO: 實際的資料庫查詢邏輯
                reply_text = f"💰 群組 {group_id} Token 查詢：\n目前餘額為 0 Token (模擬資料)。"
                logger.info(f"Group {group_id}: /查詢Token command received from user {user_id}.")
            # 可以逐步加入其他群組指令的判斷
            else:
                # 在群組中，如果不是已知指令，可以選擇不回應或提示
                # reply_text = f"群組收到未知指令：{message_text}"
                pass # 預設不回應未知群組訊息
        else: # 私人訊息
            if message_text.startswith('/'):
                reply_text = "ℹ️ 此指令需要在群組中使用喔！"
            else:
                reply_text = f"📝 您說：{event.message.text}\n請輸入 /說明 查看可用指令。"

        if reply_text:
            self.line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
            logger.info(f"Replied to {user_id} with: \"{reply_text[:50]}...\"")
        else:
            logger.info(f"No reply sent for message: '{message_text}' from {user_id} {'in group ' + group_id if is_group else ''}")

    # def _is_admin(self, user_id, group_id):
    #     # TODO: 實際的權限檢查邏輯
    #     return False # 預設都不是管理員

# 修改全域的 handle_message 函數
def handle_message(line_bot_api, event):
    """
    處理來自Line Bot的訊息，並分派給 BotCommandHandler
    """
    try:
        if event.type == "message" and event.message.type == "text":
            command_handler = BotCommandHandler(line_bot_api)
            command_handler.handle_command(event)
        # 可以後續加入處理其他事件類型，如 JoinEvent, FollowEvent 等
        # elif event.type == "join":
        #     # 處理加入群組事件
        #     group_id = event.source.group_id
        #     logger.info(f"Bot joined group: {group_id}")
        #     reply_text = "🎉 大家好！Token 管理 Bot 已加入群組！請管理員使用 /綁定Token 來啟用服務。"
        #     line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

    except Exception as e:
        logger.error(f"Error in global handle_message: {str(e)}")
        # 避免在錯誤處理中再次拋出導致循環或無回應
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="喔喔，Bot 好像有點小問題，請稍後再試 😥")
            )
        except Exception as e2:
            logger.error(f"Failed to send error reply: {str(e2)}")
