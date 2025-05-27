# -*- coding: utf-8 -*-
"""
Razer 自動儲值服務 - 使用 Selenium 進行自動化操作
"""

import os
import time
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
import pyotp
from PIL import Image
from app.database import get_db_session
from app.models import RazerLog, Group
from config.settings import Config

logger = logging.getLogger(__name__)

class RazerService:
    """Razer 自動儲值服務類別 - 使用 Selenium 自動化"""

    def __init__(self):
        """初始化 Razer 服務"""
        self.login_url = getattr(Config, 'RAZER_LOGIN_URL', 'https://razer.com/login')
        self.recharge_url = getattr(Config, 'RAZER_RECHARGE_URL', 'https://razer.com/recharge')
        self.google_auth_secret = getattr(Config, 'GOOGLE_AUTH_SECRET', '')
        self.screenshot_dir = Config.SCREENSHOT_DIR
        self.zip_output_dir = getattr(Config, 'ZIP_OUTPUT_DIR', './zip_files')
        self.chrome_driver_path = getattr(Config, 'CHROME_DRIVER_PATH', None)

        # 確保目錄存在
        os.makedirs(self.screenshot_dir, exist_ok=True)
        os.makedirs(self.zip_output_dir, exist_ok=True)

    def start_recharge_process(self, group_id: int, user_id: str, amount: float, account: str) -> bool:
        """
        開始儲值流程

        Args:
            group_id: 群組ID
            user_id: 用戶ID
            amount: 儲值金額
            account: 目標帳號

        Returns:
            是否成功啟動
        """
        try:
            # 建立儲值記錄
            with get_db_session() as db:
                razer_log = RazerLog(
                    group_id=group_id,
                    user_id=user_id,
                    razer_account=account,
                    amount=amount,
                    tokens_used=amount,
                    status='starting'
                )
                db.add(razer_log)
                db.flush()
                log_id = razer_log.id

            # 啟動自動化流程（這裡可以使用異步或背景任務）
            # 暫時同步執行，生產環境建議使用 Celery 等任務隊列
            success = self._execute_recharge_automation(log_id, account, amount)

            return success

        except Exception as e:
            logger.error(f"啟動儲值流程失敗: {str(e)}")
            return False

    def _execute_recharge_automation(self, log_id: int, account: str, amount: float) -> bool:
        """
        執行儲值自動化

        Args:
            log_id: 記錄ID
            account: 目標帳號
            amount: 儲值金額

        Returns:
            是否成功
        """
        driver = None
        screenshot_paths = []

        try:
            with get_db_session() as db:
                razer_log = db.query(RazerLog).filter_by(id=log_id).first()
                if not razer_log:
                    return False

                razer_log.status = 'processing'
                db.commit()

            # 設定 Chrome 選項
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')

            # 啟動瀏覽器
            if self.chrome_driver_path and os.path.exists(self.chrome_driver_path):
                driver = webdriver.Chrome(executable_path=self.chrome_driver_path, options=chrome_options)
            else:
                # 嘗試使用系統 PATH 中的 chromedriver
                driver = webdriver.Chrome(options=chrome_options)

            driver.maximize_window()
            wait = WebDriverWait(driver, 10)

            # 步驟 1: 登入 Razer
            logger.info("開始登入 Razer...")
            success = self._login_to_razer(driver, wait, screenshot_paths)
            if not success:
                raise Exception("Razer 登入失敗")

            # 步驟 2: 導航到儲值頁面
            logger.info("導航到儲值頁面...")
            success = self._navigate_to_recharge(driver, wait, screenshot_paths)
            if not success:
                raise Exception("導航到儲值頁面失敗")

            # 步驟 3: 執行儲值
            logger.info(f"開始儲值 {amount} 到帳號 {account}...")
            success = self._perform_recharge(driver, wait, account, amount, screenshot_paths)
            if not success:
                raise Exception("儲值操作失敗")

            # 步驟 4: 截圖確認頁面
            logger.info("截圖確認頁面...")
            self._take_confirmation_screenshot(driver, screenshot_paths)

            # 步驟 5: 建立 ZIP 檔案
            zip_path = self._create_zip_file(log_id, screenshot_paths)

            # 更新記錄狀態
            with get_db_session() as db:
                razer_log = db.query(RazerLog).filter_by(id=log_id).first()
                if razer_log:
                    razer_log.status = 'completed'
                    razer_log.screenshot_count = len(screenshot_paths)
                    razer_log.screenshot_paths = json.dumps(screenshot_paths)
                    razer_log.zip_file_path = zip_path
                    razer_log.completed_at = datetime.now()
                    db.commit()

            logger.info(f"儲值流程完成: 記錄ID {log_id}")
            return True

        except Exception as e:
            logger.error(f"儲值自動化執行失敗: {str(e)}")

            # 更新錯誤狀態
            try:
                with get_db_session() as db:
                    razer_log = db.query(RazerLog).filter_by(id=log_id).first()
                    if razer_log:
                        razer_log.status = 'failed'
                        razer_log.error_message = str(e)
                        razer_log.retry_count += 1
                        db.commit()
            except:
                pass

            return False

        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def _login_to_razer(self, driver, wait, screenshot_paths: List[str]) -> bool:
        """執行 Razer 登入"""
        try:
            # 前往登入頁面
            driver.get(self.login_url)
            time.sleep(3)

            # 截圖登入頁面
            screenshot_path = self._take_screenshot(driver, "01_login_page")
            screenshot_paths.append(screenshot_path)

            # TODO: 實作實際的登入邏輯
            # 這裡需要根據實際的 Razer 登入頁面進行調整

            # 暫時模擬登入成功
            logger.info("模擬登入成功（需要實作實際登入邏輯）")
            return True

        except Exception as e:
            logger.error(f"Razer 登入失敗: {str(e)}")
            return False

    def _navigate_to_recharge(self, driver, wait, screenshot_paths: List[str]) -> bool:
        """導航到儲值頁面"""
        try:
            # 前往儲值頁面
            driver.get(self.recharge_url)
            time.sleep(3)

            # 截圖儲值頁面
            screenshot_path = self._take_screenshot(driver, "02_recharge_page")
            screenshot_paths.append(screenshot_path)

            # TODO: 實作實際的頁面導航邏輯
            logger.info("模擬導航成功（需要實作實際導航邏輯）")
            return True

        except Exception as e:
            logger.error(f"導航到儲值頁面失敗: {str(e)}")
            return False

    def _perform_recharge(self, driver, wait, account: str, amount: float, screenshot_paths: List[str]) -> bool:
        """執行儲值操作"""
        try:
            # TODO: 實作實際的儲值邏輯
            # 1. 輸入目標帳號
            # 2. 選擇儲值金額
            # 3. 確認儲值
            # 4. 處理 OTP 驗證

            # 截圖儲值確認頁面
            screenshot_path = self._take_screenshot(driver, "03_recharge_confirm")
            screenshot_paths.append(screenshot_path)

            # 模擬 OTP 驗證
            if self.google_auth_secret:
                otp_code = self._generate_otp()
                logger.info(f"生成 OTP 驗證碼: {otp_code}")

                # TODO: 輸入 OTP 驗證碼

                # 截圖 OTP 輸入
                screenshot_path = self._take_screenshot(driver, "04_otp_input")
                screenshot_paths.append(screenshot_path)

            logger.info(f"模擬儲值成功: {account} 儲值 {amount}（需要實作實際儲值邏輯）")
            return True

        except Exception as e:
            logger.error(f"執行儲值操作失敗: {str(e)}")
            return False

    def _generate_otp(self) -> str:
        """生成 Google Authenticator OTP 驗證碼"""
        try:
            if not self.google_auth_secret:
                return ""

            totp = pyotp.TOTP(self.google_auth_secret)
            return totp.now()

        except Exception as e:
            logger.error(f"生成 OTP 失敗: {str(e)}")
            return ""

    def _take_screenshot(self, driver, step_name: str) -> str:
        """截圖並保存"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{step_name}.png"
            filepath = os.path.join(self.screenshot_dir, filename)

            driver.save_screenshot(filepath)
            logger.info(f"截圖已保存: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"截圖失敗: {str(e)}")
            return ""

    def _take_confirmation_screenshot(self, driver, screenshot_paths: List[str]):
        """截圖確認頁面"""
        try:
            screenshot_path = self._take_screenshot(driver, "05_final_confirmation")
            screenshot_paths.append(screenshot_path)
        except Exception as e:
            logger.error(f"截圖確認頁面失敗: {str(e)}")

    def _create_zip_file(self, log_id: int, screenshot_paths: List[str]) -> str:
        """建立 ZIP 檔案"""
        try:
            import zipfile

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"recharge_{log_id}_{timestamp}.zip"
            zip_filepath = os.path.join(self.zip_output_dir, zip_filename)

            with zipfile.ZipFile(zip_filepath, 'w') as zipf:
                for screenshot_path in screenshot_paths:
                    if os.path.exists(screenshot_path):
                        arcname = os.path.basename(screenshot_path)
                        zipf.write(screenshot_path, arcname)

                # 添加交易記錄
                record_content = f"""
儲值記錄 ID: {log_id}
時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
截圖數量: {len(screenshot_paths)}
                """.strip()

                zipf.writestr("record.txt", record_content)

            logger.info(f"ZIP 檔案建立完成: {zip_filepath}")
            return zip_filepath

        except Exception as e:
            logger.error(f"建立 ZIP 檔案失敗: {str(e)}")
            return ""

    def get_recharge_status(self, log_id: int) -> Optional[Dict[str, Any]]:
        """取得儲值狀態"""
        try:
            with get_db_session() as db:
                razer_log = db.query(RazerLog).filter_by(id=log_id).first()
                if not razer_log:
                    return None

                return {
                    'id': razer_log.id,
                    'status': razer_log.status,
                    'amount': razer_log.amount,
                    'account': razer_log.razer_account,
                    'screenshot_count': razer_log.screenshot_count,
                    'zip_file_path': razer_log.zip_file_path,
                    'error_message': razer_log.error_message,
                    'created_at': razer_log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'completed_at': razer_log.completed_at.strftime('%Y-%m-%d %H:%M:%S') if razer_log.completed_at else None
                }

        except Exception as e:
            logger.error(f"取得儲值狀態失敗: {str(e)}")
            return None
