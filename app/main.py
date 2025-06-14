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

from app.bot_handler import handle_message as process_line_event
from config.settings import Config
from .database import init_database, get_db_session
from .models import SystemConfig

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("app.main")

print("--- app/main.py: Script started, imports successful ---")
logger.info("--- app/main.py: Script started, imports successful (logger) ---")

def create_app() -> FastAPI:
    """創建FastAPI應用程式"""
    logger.info("--- app/main.py: create_app() called ---")
    app = FastAPI(
        title="遊戲自動化儲值 Line Bot",
        description="一個基於 Line Bot 的遊戲自動化儲值系統，支援 Razer Gold 支付和自動化操作。",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    logger.info("--- app/main.py: FastAPI app instance created in create_app ---")

    # 驗證配置
    logger.info("--- app/main.py: Validating config ---")
    if not Config.validate_config():
        logger.error("--- app/main.py: Config validation FAILED ---")
        raise RuntimeError("配置驗證失敗，請檢查環境變數設定")
    logger.info("--- app/main.py: Config validation PASSED ---")

    # Line Bot API 設定
    logger.info("--- app/main.py: Initializing LineBotApi and WebhookHandler ---")
    try:
        line_bot_api = LineBotApi(Config.CHANNEL_ACCESS_TOKEN)
        handler = WebhookHandler(Config.CHANNEL_SECRET)
        logger.info("--- app/main.py: LineBotApi and WebhookHandler initialized successfully ---")
    except Exception as e:
        logger.error(f"--- app/main.py: ERROR initializing LineBotApi/WebhookHandler: {e} ---")
        raise

    @app.on_event("startup")
    async def startup_event():
        print("--- app/main.py: Application startup event triggered ---")
        logger.info("--- app/main.py: Application startup event triggered (logger) ---")
        try:
            logger.info("--- app/main.py: Initializing database (creating tables if not exist) ---")
            init_database()
            logger.info("--- app/main.py: Database initialization complete/checked ---")

            logger.info("--- app/main.py: Seeding default system configs ---")
            seed_default_system_configs()
            logger.info("--- app/main.py: Default system configs seeded/checked ---")

        except Exception as e:
            logger.error(f"--- app/main.py: Database initialization or seeding FAILED: {e} ---")
            import traceback
            logger.error(traceback.format_exc())
            # 根據情況，你可能希望應用程式在這裡失敗並退出

    @app.get("/")
    def read_root():
        print("--- app/main.py: Root endpoint / called ---")
        logger.info("--- app/main.py: Root endpoint / was called (logger) ---")
        return {"message": "Minimal app is running! Check Zeabur logs for '---' messages."}

    @app.get("/health")
    def health_check():
        print("--- app/main.py: Health endpoint /health called ---")
        logger.info("--- app/main.py: Health endpoint /health was called (logger) ---")
        return {"status": "healthy"}

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
        logger.info("--- app/main.py: /callback endpoint hit ---")
        signature = request.headers.get('X-Line-Signature')
        body = await request.body()
        body_text = body.decode('utf-8')
        logger.debug(f"Request body: {body_text}")
        logger.debug(f"Signature: {signature}")

        try:
            handler.handle(body_text, signature)
            logger.info("--- app/main.py: Webhook event processed by handler ---")
        except InvalidSignatureError:
            logger.warning("--- app/main.py: Invalid signature. Check your CHANNEL_SECRET. ---")
            raise HTTPException(status_code=400, detail="Invalid signature")
        except Exception as e:
            logger.error(f"--- app/main.py: Error processing webhook: {str(e)} ---")
            import traceback
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Error processing webhook")
        return {"status": "ok"}

    # === Line 事件處理器 ===

    @handler.add(MessageEvent, message=TextMessage)
    def handle_text_message_event(event):
        """處理文字訊息"""
        try:
            user_id = event.source.user_id
            message_text = event.message.text
            logger.info(f"--- app/main.py: TextMessage event received: {message_text} ---")

            process_line_event(line_bot_api, event)

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
    def handle_follow_event(event):
        """處理用戶追蹤事件"""
        try:
            user_id = event.source.user_id
            logger.info(f"--- app/main.py: FollowEvent received from user: {user_id} ---")

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
    def handle_join_event(event):
        """處理 Bot 被加入群組事件"""
        try:
            group_id = event.source.group_id if hasattr(event.source, 'group_id') else 'unknown'
            logger.info(f"--- app/main.py: JoinEvent received. Bot joined group: {group_id} ---")

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
    async def test_config_endpoint():
        """測試配置是否正確載入"""
        from config.settings import Config

        return {
            "channel_access_token_exists": bool(Config.CHANNEL_ACCESS_TOKEN),
            "channel_secret_exists": bool(Config.CHANNEL_SECRET),
            "channel_access_token_length": len(Config.CHANNEL_ACCESS_TOKEN) if Config.CHANNEL_ACCESS_TOKEN else 0,
            "channel_secret_length": len(Config.CHANNEL_SECRET) if Config.CHANNEL_SECRET else 0
        }

    @app.post("/callback-debug")
    async def callback_debug_endpoint(request: Request):
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
    async def line_webhook_test_endpoint(request: Request):
        """測試版 callback，跳過簽名驗證"""
        try:
            # 取得 request body
            body = await request.body()
            body_text = body.decode('utf-8')

            logger.info(f"--- app/main.py: /callback-test endpoint hit ---")
            logger.info(f"--- app/main.py: /callback-test received body: {body_text[:100]}... ---")

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
                    process_line_event(line_bot_api, fake_event)

            return {"status": "ok", "message": "Test event processed (simulated)"}

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

    print("--- app/main.py: End of file, app instance and routes defined ---")
    logger.info("--- app/main.py: End of file, app instance and routes defined (logger) ---")

    return app

# 創建應用程式實例
logger.info("--- app/main.py: Calling create_app() to create app instance ---")
app = create_app()
logger.info("--- app/main.py: FastAPI app instance 'app' created globally ---")

# 在 create_app() 函數的外部，或者一個適合的地方，定義 seed_default_system_configs
def seed_default_system_configs():
    default_configs = [
        {
            'config_key': 'bank_account_info',
            'config_value': '銀行：範例銀行 (007)\n帳號：123-456-7890123\n戶名：自動化儲值專戶',
            'description': '用於 Token 充值的銀行帳戶資訊。'
        },
        {
            'config_key': 'min_deposit_amount',
            'config_value': '100',
            'description': '用戶單次充值的最低金額 (NT$)'
        },
        {
            'config_key': 'token_exchange_rate',
            'config_value': '1.0',
            'description': '新台幣與 Token 的兌換比率 (1 NT$ = X Token)'
        },
        {
            'config_key': 'seagm_username',
            'config_value': 'kk5010760107@gmail.com',
            'description': '用於登入 SEAGM 網站的帳號。'
        },
        {
            'config_key': 'seagm_password',
            'config_value': 'C5dpLqUC#cq#5Rc',
            'description': '用於登入 SEAGM 網站的密碼。'
        }
        # 你可以在這裡加入更多預設系統設定
    ]

    try:
        with get_db_session() as db:
            for config_data in default_configs:
                existing_config = db.query(SystemConfig).filter_by(config_key=config_data['config_key']).first()
                if not existing_config:
                    new_config = SystemConfig(**config_data)
                    db.add(new_config)
                    logger.info(f"Seeded system config: {config_data['config_key']} = {config_data['config_value']}")
                # else: # 可選：如果已存在，可以考慮更新或忽略
                    # logger.info(f"System config already exists: {config_data['config_key']}")
            db.commit()
    except Exception as e:
        logger.error(f"Error seeding default system configs: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # 即使 seeding 失敗，我們可能還是希望應用程式繼續運行
