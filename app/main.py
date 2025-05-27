# -*- coding: utf-8 -*-
"""
主要應用程式進入點 - FastAPI 版本
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, TextMessage, ImageMessage, VideoMessage, AudioMessage,
    FileMessage, LocationMessage, StickerMessage,
    PostbackEvent, FollowEvent, UnfollowEvent, JoinEvent, LeaveEvent,
    MemberJoinedEvent, MemberLeftEvent, BeaconEvent
)
import os
import logging
from dotenv import load_dotenv

from app.bot_handler import handle_message
from config.settings import Config

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """創建FastAPI應用程式"""
    app = FastAPI(
        title="遊戲自動化儲值 Line Bot",
        description="一個基於 Line Bot 的遊戲自動化儲值系統，支援 Razer Gold 支付和自動化操作。",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # 驗證配置
    if not Config.validate_config():
        raise RuntimeError("配置驗證失敗，請檢查環境變數設定")

    # Line Bot API 設定
    line_bot_api = LineBotApi(Config.CHANNEL_ACCESS_TOKEN)
    handler = WebhookHandler(Config.CHANNEL_SECRET)

    @app.get("/", response_class=HTMLResponse)
    async def index():
        """首頁 - 健康檢查"""
        return """
        <html>
            <head>
                <title>遊戲自動化儲值 Line Bot</title>
                <meta charset="utf-8">
            </head>
            <body>
                <h1>🎮 遊戲自動化儲值 Line Bot</h1>
                <p>系統正在運行中！</p>
                <ul>
                    <li>✅ Line Bot API 已連接</li>
                    <li>✅ Webhook 已準備就緒</li>
                    <li>✅ 自動化服務已啟動</li>
                </ul>
                <p><a href="/docs">查看 API 文檔</a></p>
            </body>
        </html>
        """

    @app.get("/health")
    async def health_check():
        """健康檢查端點"""
        return {
            "status": "healthy",
            "service": "game-automation-linebot",
            "version": "1.0.0",
            "line_bot_connected": bool(Config.CHANNEL_ACCESS_TOKEN and Config.CHANNEL_SECRET)
        }

    @app.get("/webhook/test")
    async def webhook_test():
        """測試 Webhook 是否正常運作"""
        return {
            "status": "ok",
            "message": "Webhook endpoint is working",
            "webhook_url": "/callback",
            "supported_events": [
                "TextMessage", "ImageMessage", "LocationMessage", "StickerMessage",
                "PostbackEvent", "FollowEvent", "UnfollowEvent", "JoinEvent", "LeaveEvent"
            ]
        }

    @app.post("/callback")
    async def line_webhook(request: Request):
        """
        Line Bot Webhook 端點

        接收來自 Line 平台的所有事件，包括：
        - 文字訊息
        - 圖片、影片、音檔等媒體訊息
        - 用戶追蹤/取消追蹤事件
        - Postback 事件
        - 位置訊息等
        """
        try:
            # 取得 X-Line-Signature header
            signature = request.headers.get('X-Line-Signature')
            if not signature:
                logger.error("Missing X-Line-Signature header")
                raise HTTPException(status_code=400, detail="Missing X-Line-Signature header")

            # 取得 request body
            body = await request.body()
            if not body:
                logger.error("Empty request body")
                raise HTTPException(status_code=400, detail="Empty request body")

            body_text = body.decode('utf-8')

            # 記錄收到的請求（但不記錄敏感資料）
            logger.info(f"收到 Line Webhook 請求，大小: {len(body_text)} bytes")

            # 驗證 signature
            try:
                handler.handle(body_text, signature)
                logger.info("Line Webhook 事件處理成功")
            except InvalidSignatureError as e:
                logger.warning("Invalid signature. Please check your channel access token/channel secret.")
                raise HTTPException(status_code=400, detail="Invalid signature")
            except Exception as e:
                logger.error(f"處理 Line 事件時發生錯誤: {str(e)}")
                raise HTTPException(status_code=500, detail="Error processing Line event")

            return {"status": "ok", "message": "Event processed successfully"}

        except HTTPException:
            # 重新拋出 HTTP 異常
            raise
        except Exception as e:
            logger.error(f"Webhook 處理發生未預期的錯誤: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    # === Line 事件處理器 ===

    @handler.add(MessageEvent, message=TextMessage)
    def handle_text_message(event):
        """處理文字訊息"""
        try:
            user_id = event.source.user_id
            message_text = event.message.text
            logger.info(f"收到用戶 {user_id} 的文字訊息: {message_text}")

            handle_message(line_bot_api, event)

        except LineBotApiError as e:
            logger.error(f"Line Bot API 錯誤: {str(e)}")
        except Exception as e:
            logger.error(f"處理文字訊息時發生錯誤: {str(e)}")

    @handler.add(MessageEvent, message=ImageMessage)
    def handle_image_message(event):
        """處理圖片訊息"""
        try:
            user_id = event.source.user_id
            logger.info(f"收到用戶 {user_id} 的圖片訊息")

            # 可以在這裡實作圖片處理邏輯
            # 例如：保存圖片、分析圖片內容等

            from linebot.models import TextSendMessage
            reply_message = TextSendMessage(text="📸 已收到您的圖片！")
            line_bot_api.reply_message(event.reply_token, reply_message)

        except LineBotApiError as e:
            logger.error(f"處理圖片訊息時 Line Bot API 錯誤: {str(e)}")
        except Exception as e:
            logger.error(f"處理圖片訊息時發生錯誤: {str(e)}")

    @handler.add(MessageEvent, message=LocationMessage)
    def handle_location_message(event):
        """處理位置訊息"""
        try:
            user_id = event.source.user_id
            location = event.message
            logger.info(f"收到用戶 {user_id} 的位置訊息: {location.address}")

            from linebot.models import TextSendMessage
            reply_text = f"📍 已收到您的位置資訊:\n地址: {location.address}\n緯度: {location.latitude}\n經度: {location.longitude}"
            reply_message = TextSendMessage(text=reply_text)
            line_bot_api.reply_message(event.reply_token, reply_message)

        except LineBotApiError as e:
            logger.error(f"處理位置訊息時 Line Bot API 錯誤: {str(e)}")
        except Exception as e:
            logger.error(f"處理位置訊息時發生錯誤: {str(e)}")

    @handler.add(MessageEvent, message=StickerMessage)
    def handle_sticker_message(event):
        """處理貼圖訊息"""
        try:
            user_id = event.source.user_id
            sticker = event.message
            logger.info(f"收到用戶 {user_id} 的貼圖訊息: package_id={sticker.package_id}, sticker_id={sticker.sticker_id}")

            from linebot.models import StickerSendMessage
            # 回應一個貼圖
            reply_message = StickerSendMessage(package_id='1', sticker_id='1')
            line_bot_api.reply_message(event.reply_token, reply_message)

        except LineBotApiError as e:
            logger.error(f"處理貼圖訊息時 Line Bot API 錯誤: {str(e)}")
        except Exception as e:
            logger.error(f"處理貼圖訊息時發生錯誤: {str(e)}")

    @handler.add(PostbackEvent)
    def handle_postback(event):
        """處理 Postback 事件（來自按鈕點擊）"""
        try:
            user_id = event.source.user_id
            postback_data = event.postback.data
            logger.info(f"收到用戶 {user_id} 的 Postback 事件: {postback_data}")

            # 解析 Postback 資料並執行相應動作
            if postback_data.startswith('action='):
                action = postback_data.split('=')[1]

                if action == 'check_balance':
                    # 處理查詢餘額
                    from linebot.models import TextSendMessage
                    reply_message = TextSendMessage(text="正在查詢您的餘額...")
                    line_bot_api.reply_message(event.reply_token, reply_message)

                elif action == 'start_topup':
                    # 處理開始儲值
                    from linebot.models import TextSendMessage
                    reply_message = TextSendMessage(text="正在啟動自動化儲值流程...")
                    line_bot_api.reply_message(event.reply_token, reply_message)

                else:
                    # 未知動作
                    from linebot.models import TextSendMessage
                    reply_message = TextSendMessage(text="未知的操作，請重新選擇。")
                    line_bot_api.reply_message(event.reply_token, reply_message)

        except LineBotApiError as e:
            logger.error(f"處理 Postback 事件時 Line Bot API 錯誤: {str(e)}")
        except Exception as e:
            logger.error(f"處理 Postback 事件時發生錯誤: {str(e)}")

    @handler.add(FollowEvent)
    def handle_follow(event):
        """處理用戶追蹤事件"""
        try:
            user_id = event.source.user_id
            logger.info(f"新用戶追蹤: {user_id}")

            # 歡迎新用戶
            from linebot.models import TextSendMessage
            welcome_text = """🎮 歡迎使用遊戲自動化儲值 Line Bot！

我可以幫您：
✅ 自動化遊戲儲值
✅ 查詢代幣餘額
✅ 管理交易記錄
✅ 設定帳號資訊

請輸入「開始」或「start」來開始使用！"""

            welcome_message = TextSendMessage(text=welcome_text)
            line_bot_api.reply_message(event.reply_token, welcome_message)

        except LineBotApiError as e:
            logger.error(f"處理追蹤事件時 Line Bot API 錯誤: {str(e)}")
        except Exception as e:
            logger.error(f"處理追蹤事件時發生錯誤: {str(e)}")

    @handler.add(UnfollowEvent)
    def handle_unfollow(event):
        """處理用戶取消追蹤事件"""
        try:
            user_id = event.source.user_id
            logger.info(f"用戶取消追蹤: {user_id}")

            # 可以在這裡執行清理動作，如更新資料庫等

        except Exception as e:
            logger.error(f"處理取消追蹤事件時發生錯誤: {str(e)}")

    @handler.add(JoinEvent)
    def handle_join(event):
        """處理 Bot 被加入群組事件"""
        try:
            group_id = event.source.group_id if hasattr(event.source, 'group_id') else 'unknown'
            logger.info(f"Bot 被加入群組: {group_id}")

            from linebot.models import TextSendMessage
            welcome_text = """🎮 感謝將我加入此群組！

我是遊戲自動化儲值機器人，可以協助群組成員進行：
✅ 遊戲自動化儲值
✅ 餘額查詢
✅ 交易管理

請私訊我來開始使用服務！"""

            welcome_message = TextSendMessage(text=welcome_text)
            line_bot_api.reply_message(event.reply_token, welcome_message)

        except LineBotApiError as e:
            logger.error(f"處理加入群組事件時 Line Bot API 錯誤: {str(e)}")
        except Exception as e:
            logger.error(f"處理加入群組事件時發生錯誤: {str(e)}")

    @handler.add(LeaveEvent)
    def handle_leave(event):
        """處理 Bot 被移出群組事件"""
        try:
            group_id = event.source.group_id if hasattr(event.source, 'group_id') else 'unknown'
            logger.info(f"Bot 被移出群組: {group_id}")

            # 可以在這裡執行清理動作

        except Exception as e:
            logger.error(f"處理離開群組事件時發生錯誤: {str(e)}")

    # 預設事件處理器暫時註解，因為參數問題
    # @handler.default
    # def default_handler(event):
    #     """處理未定義的事件"""
    #     logger.info(f"收到未處理的事件類型: {type(event)}")
    #     logger.debug(f"事件內容: {event}")
    #     # 不回應未知事件，避免錯誤

    @app.post("/payment/callback")
    async def payment_callback(request: Request):
        """Razer 支付回調端點"""
        try:
            # 處理支付回調邏輯
            body = await request.body()
            # 這裡會實作 Razer 支付回調處理
            logger.info(f"收到支付回調: {body}")

            return {"status": "success"}

        except Exception as e:
            logger.error(f"支付回調處理錯誤: {str(e)}")
            raise HTTPException(status_code=500, detail="Payment callback error")

    @app.get("/payment/return")
    async def payment_return(request: Request):
        """支付完成返回頁面"""
        return HTMLResponse("""
        <html>
            <head>
                <title>支付完成</title>
                <meta charset="utf-8">
            </head>
            <body>
                <h1>💳 支付處理中</h1>
                <p>您的支付正在處理中，請稍候...</p>
                <p>處理完成後會透過 Line Bot 通知您。</p>
                <script>
                    setTimeout(function() {
                        window.close();
                    }, 3000);
                </script>
            </body>
        </html>
        """)

    @app.get("/test-config")
    async def test_config():
        """測試配置是否正確載入"""
        from config.settings import Config

        return {
            "channel_access_token_exists": bool(Config.CHANNEL_ACCESS_TOKEN),
            "channel_secret_exists": bool(Config.CHANNEL_SECRET),
            "channel_access_token_length": len(Config.CHANNEL_ACCESS_TOKEN) if Config.CHANNEL_ACCESS_TOKEN else 0,
            "channel_secret_length": len(Config.CHANNEL_SECRET) if Config.CHANNEL_SECRET else 0
        }

    @app.post("/callback-debug")
    async def callback_debug(request: Request):
        """Debug 版本的 callback，輸出詳細資訊"""
        try:
            # 取得所有 headers
            headers = dict(request.headers)

            # 取得 body
            body = await request.body()
            body_text = body.decode('utf-8')

            # 取得簽名
            signature = headers.get('x-line-signature', 'Missing')

            # 檢查配置
            from config.settings import Config
            channel_secret_length = len(Config.CHANNEL_SECRET) if Config.CHANNEL_SECRET else 0

            return {
                "status": "debug_success",
                "headers": headers,
                "body_length": len(body_text),
                "signature_exists": signature != 'Missing',
                "signature_value": signature[:20] + "..." if signature != 'Missing' else 'Missing',
                "channel_secret_length": channel_secret_length,
                "config_valid": bool(Config.CHANNEL_SECRET and Config.CHANNEL_ACCESS_TOKEN)
            }

        except Exception as e:
            return {"error": str(e)}

    @app.post("/callback-test")
    async def line_webhook_test(request: Request):
        """測試版 callback，跳過簽名驗證"""
        try:
            # 取得 request body
            body = await request.body()
            body_text = body.decode('utf-8')

            logger.info(f"收到測試 Webhook 請求，大小: {len(body_text)} bytes")

            # 解析事件（不驗證簽名）
            import json
            from linebot.models import MessageEvent, TextMessage

            events_data = json.loads(body_text)

            # 處理每個事件
            for event_data in events_data.get('events', []):
                if event_data.get('type') == 'message' and event_data.get('message', {}).get('type') == 'text':
                    # 建立假的事件物件進行測試
                    class FakeEvent:
                        def __init__(self, data):
                            self.reply_token = data.get('replyToken')
                            self.source = type('Source', (), {
                                'user_id': data.get('source', {}).get('userId'),
                                'group_id': data.get('source', {}).get('groupId')
                            })()
                            self.message = type('Message', (), {
                                'text': data.get('message', {}).get('text')
                            })()

                    fake_event = FakeEvent(event_data)
                    handle_message(line_bot_api, fake_event)

            return {"status": "ok", "message": "Test event processed successfully"}

        except Exception as e:
            logger.error(f"測試 Webhook 處理錯誤: {str(e)}")
            return {"status": "error", "message": str(e)}

    # 添加異常處理器
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": exc.detail}
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"未處理的異常: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={"message": "Internal server error"}
        )

    return app

# 創建應用程式實例
app = create_app()

if __name__ == "__main__":
    import uvicorn

    # 開發環境啟動
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )
