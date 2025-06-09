# app/bot_handler.py (更新 /查詢Token 和 /購買Token 功能)
from linebot.models import TextSendMessage
import logging
from sqlalchemy.exc import IntegrityError
import threading

# 從 .database 導入 get_db_session，從 .models 導入所有需要的模型
from .database import get_db_session
from .models import Group, User, GroupMember, TokenLog, SystemConfig # 新增 SystemConfig
from .services.playwright_service import PlaywrightService

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
                    reply_text = f"⚠️ 本群組 (ID: ...{group_id[-6:]}) 已經綁定過 Token 帳戶了！\n目前餘額: {existing_group.token_balance:.1f} Token"
                    self.line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
                    return

                # 暫時使用預設名稱，之後可以考慮從 Line API 獲取
                group_name = f"群組_{group_id[-6:]}"

                # 建立新群組
                new_group = Group(
                    line_group_id=group_id, group_name=group_name,
                    token_balance=0.0, is_active=True
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
                    f"💰 目前 Token 餘額: {new_group.token_balance:.1f}。"
                )
                logger.info(f"Group {group_id} successfully bound by user {user_id}. New group ID: {new_group.id}")
        except IntegrityError as e:
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
                    # 查詢最近5筆交易記錄
                    recent_logs = db.query(TokenLog).filter(TokenLog.group_id == group.id).order_by(TokenLog.created_at.desc()).limit(5).all()
                    logs_str = "\n\n📜 最近交易記錄：\n"
                    if recent_logs:
                        for log in recent_logs:
                            log_type_emoji = "➕" if log.amount > 0 else ("➖" if log.amount < 0 else "⚙️")
                            description_text = log.description[:20] if log.description else "系統操作"
                            logs_str += f"{log.created_at.strftime('%m/%d %H:%M')} {log_type_emoji} {abs(log.amount):.1f} ({description_text})\n"
                    else:
                        logs_str += "(尚無交易記錄)\n"

                    reply_text = (
                        f"💰 群組 '{group.group_name}' Token 資訊：\n"
                        f"💳 目前餘額: {group.token_balance:.1f} Token。"
                        f"{logs_str}"
                    )
        except Exception as e:
            logger.error(f"Error querying token for group {group_id}: {e}")
            reply_text = "❌ 查詢 Token 時發生錯誤。"
        self.line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

    def _handle_buy_token_info(self, event):
        group_id = event.source.group_id
        user_id = event.source.user_id
        logger.info(f"Group {group_id}: Received /購買Token command from user {user_id}")
        reply_text = ""
        try:
            with get_db_session() as db:
                group = db.query(Group).filter(Group.line_group_id == group_id).first()
                if not group:
                    reply_text = f"⚠️ 本群組 (ID: ...{group_id[-6:]}) 尚未綁定 Token 帳戶。\n請管理員使用 `/綁定Token` 指令。"
                else:
                    bank_info_setting = db.query(SystemConfig).filter(SystemConfig.config_key == 'bank_account_info').first()
                    min_deposit_setting = db.query(SystemConfig).filter(SystemConfig.config_key == 'min_deposit_amount').first()
                    token_rate_setting = db.query(SystemConfig).filter(SystemConfig.config_key == 'token_exchange_rate').first()

                    bank_info = bank_info_setting.config_value if bank_info_setting and bank_info_setting.config_value else "請洽詢管理員提供匯款資訊。"
                    min_deposit = min_deposit_setting.config_value if min_deposit_setting and min_deposit_setting.config_value else "100"
                    token_rate = token_rate_setting.config_value if token_rate_setting and token_rate_setting.config_value else "1.0"

                    reply_text = (
                        f"💳 Token 充值資訊 ({group.group_name}) 💳\n\n"
                        f"💹 兌換比率: 1 NT$ = {float(token_rate):.1f} Token\n"
                        f"💵 最低充值: NT$ {min_deposit}\n\n"
                        f"🏦 轉帳資訊：\n{bank_info}\n\n"
                        f"⚠️ 注意：轉帳時請務必在備註欄填寫您的 Line 名稱或群組ID (例如：...{group_id[-6:]})，以便快速對帳！\n"
                        f"⏳ 對帳完成後，Token 將自動加入群組餘額。"
                    )
        except Exception as e:
            logger.error(f"Error getting buy token info for group {group_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            reply_text = "❌ 索取購買資訊時發生錯誤。"
        self.line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

    def _recharge_worker(self, event, token_cost):
        """在背景執行 Playwright 自動化儲值的工人函式"""
        group_id = event.source.group_id
        user_id = event.source.user_id

        try:
            parts = event.message.text.strip().split()
            product_id = parts[1]
            player_id = parts[2]
            player_server = parts[3]
            game_name = "Identity V Echoes(Global)" # 目前暫時寫死

            # 1. 從資料庫獲取 SEAGM 登入憑證
            with get_db_session() as db:
                seagm_user_cfg = db.query(SystemConfig).filter_by(config_key='seagm_username').first()
                seagm_pass_cfg = db.query(SystemConfig).filter_by(config_key='seagm_password').first()
                if not (seagm_user_cfg and seagm_pass_cfg and seagm_user_cfg.config_value and seagm_pass_cfg.config_value):
                    raise ValueError("系統未設定 SEAGM 帳號或密碼。")
                seagm_username = seagm_user_cfg.config_value
                seagm_password = seagm_pass_cfg.config_value

            # 2. 執行 Playwright 自動化
            logger.info(f"Starting Playwright automation for group {group_id}")
            service = PlaywrightService()
            success, message = service.run_seagm_automation(
                seagm_username=seagm_username,
                seagm_password=seagm_password,
                game_name=game_name,
                player_id=player_id,
                player_server=player_server,
                product_id=product_id
            )
            logger.info(f"Playwright automation finished for group {group_id}. Success: {success}")

            # 3. 處理自動化結果
            if success:
                # 3a. 扣除 Token
                with get_db_session() as db:
                    group = db.query(Group).filter(Group.line_group_id == group_id).with_for_update().first()
                    user = db.query(User).filter(User.line_user_id == user_id).first()

                    if group.token_balance < token_cost:
                        final_message = f"⚠️ 儲值流程已完成，但扣款失敗！\n原因: Token 餘額不足 ({group.token_balance:.1f})，需要 {token_cost:.1f}。\n請聯繫管理員處理此筆交易。"
                    else:
                        balance_before = group.token_balance
                        group.token_balance -= token_cost
                        balance_after = group.token_balance
                        db.add(TokenLog(
                            group_id=group.id, user_id=user.id if user else None,
                            transaction_type='withdraw', amount=-token_cost,
                            balance_before=balance_before, balance_after=balance_after,
                            description=f"儲值 {game_name} ({product_id})",
                            operator=user.display_name if user else "System"
                        ))
                        db.commit()
                        final_message = f"✅ 儲值成功，已扣款！\n\n- 遊戲: {game_name}\n- 商品: {product_id}\n- 玩家ID: {player_id}\n- 花費: {token_cost:.1f} Token\n- 剩餘: {balance_after:.1f} Token\n\n{message}"
            else:
                # 3b. 回報失敗
                final_message = f"❌ 儲值失敗！\n\n- 遊戲: {game_name}\n- 原因: {message}\n\n此次未扣除任何 Token。"

            # 4. 推播最終結果到群組
            self.line_bot_api.push_message(group_id, TextSendMessage(text=final_message))

        except Exception as e:
            logger.error(f"Error in recharge worker for group {group_id}: {e}", exc_info=True)
            self.line_bot_api.push_message(group_id, TextSendMessage(text=f"⚙️ 儲值機器人發生系統錯誤，請聯繫管理員。\n錯誤: {e}"))

    def _handle_recharge(self, event):
        """處理 /儲值 指令的初始部分"""
        group_id = event.source.group_id
        logger.info(f"Group {group_id}: Received recharge command")

        try:
            parts = event.message.text.strip().split()
            if len(parts) != 5:
                reply_text = "⚠️ 指令格式錯誤！\n應為: /儲值 <商品ID> <玩家ID> <伺服器> <Token價格>\n例如: /儲值 13664 12345678 Asia 35.2"
                self.line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
                return

            _command, _product_id, _player_id, _player_server, cost_str = parts

            try:
                token_cost = float(cost_str)
            except ValueError:
                reply_text = "⚠️ Token 價格必須是數字！"
                self.line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
                return

            with get_db_session() as db:
                group = db.query(Group).filter(Group.line_group_id == group_id).first()
                if not group:
                    reply_text = "⚠️ 本群組尚未綁定 Token 帳戶。"
                    self.line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
                    return

                if group.token_balance < token_cost:
                    reply_text = f"📉 Token 餘額不足！\n\n- 目前餘額: {group.token_balance:.1f}\n- 本次需要: {token_cost:.1f}\n- 不足: {token_cost - group.token_balance:.1f}"
                    self.line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
                    return

            # 在背景執行緒中啟動 Playwright 任務
            worker_thread = threading.Thread(target=self._recharge_worker, args=(event, token_cost))
            worker_thread.start()

            # 立即回覆使用者，告知請求已在處理中
            reply_text = f"⏳ 儲值請求已接收！\n\n- 遊戲: 第五人格\n- 商品ID: {_product_id}\n- 價格: {token_cost:.1f} Token\n\n正在啟動自動化流程，完成後將會通知。請勿重複發送指令。"
            self.line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

        except Exception as e:
            logger.error(f"Error handling recharge for group {group_id}: {e}", exc_info=True)
            self.line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"❌ 處理儲值指令時發生錯誤: {e}"))

    def handle_command(self, event):
        user_id = event.source.user_id
        message_text = event.message.text.strip().lower()
        is_group = hasattr(event.source, 'group_id')
        group_id = event.source.group_id if is_group else "N/A" # 確保 group_id 總是有值

        logger.info(f"Received message: '{message_text}' from user: {user_id} in {'group: ' + group_id if is_group and group_id != 'N/A' else 'private chat'}")
        reply_text = None

        if message_text in ['hello', 'hi', '你好', '哈囉']:
            reply_text = f"👋 您好 {self._get_user_display_name(user_id)}！很高興為您服務。"
        elif message_text in ['開始', 'start']:
            reply_text = "🚀 歡迎使用！輸入 /說明 查看可用指令。"
        elif message_text == '/說明' or message_text == '/help':
            base_commands = (
                "🤖 Line Bot 功能說明 (v0.3)\n\n"
                "--- 基本指令 ---\n"
                "• Hello / 你好 - 基本問候\n"
                "• 開始 / start - 顯示開始訊息\n"
                "• /說明 (/help) - 顯示此說明\n\n"
                "--- 群組專用指令 ---\n"
                "• /綁定Token - (群組)綁定Token帳戶\n"
                "• /查詢Token - (群組)查詢餘額與記錄\n"
                "• /購買Token - (群組)顯示購買Token資訊\n"
                "• /儲值 <商品ID> <玩家ID> <伺服器> <價格> - (群組)執行自動化儲值"
            )
            reply_text = base_commands + "\n\n🔧 更多功能陸續推出！"

        elif is_group:
            if message_text == '/綁定token':
                self._handle_bind_token(event)
                return
            elif message_text == '/查詢token':
                self._handle_query_token(event)
                return
            elif message_text == '/購買token':
                self._handle_buy_token_info(event)
                return
            elif message_text.startswith('/儲值'):
                self._handle_recharge(event)
                return
            else:
                pass
        else:
            if message_text.startswith('/'):
                reply_text = "ℹ️ 此指令需要在群組中使用喔！"
            else:
                reply_text = f"📝 您說：{event.message.text}\n請輸入 /說明 查看可用指令。"

        if reply_text:
            self.line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
            logger.info(f"Replied to {user_id} with: \"{reply_text[:50]}...\"")

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
