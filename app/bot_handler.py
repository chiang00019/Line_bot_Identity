# -*- coding: utf-8 -*-
"""
Line Bot 訊息處理邏輯 - 簡化版
"""

from linebot.models import TextSendMessage
import logging

logger = logging.getLogger(__name__)

def handle_message(line_bot_api, event):
    """
    處理來自Line Bot的訊息

    Args:
        line_bot_api: Line Bot API 實例
        event: Line Bot 事件物件
    """
    try:
        user_id = event.source.user_id
        message_text = event.message.text.strip().lower()

        logger.info(f"收到用戶 {user_id} 的訊息: {message_text}")

        # 基本回應邏輯
        if message_text in ['hello', 'hi', '你好', '哈囉']:
            reply_text = "👋 您好！歡迎使用Line Bot！\n\n我目前支援以下功能：\n• 基本對話\n• 群組管理\n• Token系統（開發中）"

        elif message_text in ['開始', 'start']:
            reply_text = "🚀 歡迎開始使用！\n\n可用指令：\n• /綁定Token - 綁定群組帳戶\n• /說明 - 查看完整說明\n• Hello - 基本問候"

        elif message_text == '/綁定token':
            if hasattr(event.source, 'group_id'):
                reply_text = "✅ 群組Token綁定功能\n\n此功能正在開發中，敬請期待！\n目前您可以使用基本對話功能。"
            else:
                reply_text = "⚠️ 請在群組中使用此功能"

        elif message_text in ['/說明', '/help']:
            reply_text = """🤖 Line Bot 使用說明

基本功能：
• Hello/你好 - 問候
• 開始/start - 開始使用
• /綁定Token - 群組功能（開發中）
• /說明 - 顯示此說明

📍 狀態：基礎版本運行中
🔧 更多功能開發中...

如有問題請聯繫管理員！"""

        else:
            # 預設回應
            reply_text = f"📝 您說：{event.message.text}\n\n我是Line Bot，目前還在學習中！\n試試輸入「Hello」或「/說明」吧！"

        # 建立回覆訊息
        reply_message = TextSendMessage(text=reply_text)

        # 回覆訊息
        line_bot_api.reply_message(event.reply_token, reply_message)

        logger.info(f"成功回覆用戶 {user_id}")

    except Exception as e:
        logger.error(f"處理訊息時發生錯誤: {str(e)}")
        try:
            error_message = TextSendMessage(text="❌ 系統發生錯誤，請稍後再試。")
            line_bot_api.reply_message(event.reply_token, error_message)
        except Exception as reply_error:
            logger.error(f"回覆錯誤訊息失敗: {str(reply_error)}")
