#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zeabur 專用啟動檔案
簡化的 Line Bot 啟動器，專門為 Zeabur 平台優化
"""

import os
import sys
import logging
from pathlib import Path

# 確保專案根目錄在 Python 路徑中
print("--- zeabur_start.py: Adding project root to sys.path ---")
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
print(f"--- zeabur_start.py: sys.path[0] = {sys.path[0]} ---")

# 設定日誌
print("--- zeabur_start.py: Configuring logging ---")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
print("--- zeabur_start.py: Logging configured ---")

def main():
    """主啟動函數"""
    print("--- zeabur_start.py: main() function started ---")
    try:
        port = os.getenv("PORT", "5000")
        print(f"--- zeabur_start.py: PORT from env: {os.getenv('PORT')}, Effective PORT: {port} ---")

        logger.info("🚀 啟動 Line Bot Token 管理系統")
        logger.info(f"📦 部署平台: Zeabur")
        logger.info(f"🌐 服務端口: {port}")

        required_vars = ["CHANNEL_ACCESS_TOKEN", "CHANNEL_SECRET"]
        print(f"--- zeabur_start.py: Checking required_vars: {required_vars} ---")

        # 檢查並印出環境變數的值 (部分遮蔽敏感資訊)
        for var_name in required_vars:
            var_value = os.getenv(var_name)
            if var_value:
                # 遮蔽大部分 token 和 secret，只顯示前後幾個字符
                display_value = f"{var_value[:4]}...{var_value[-4:]}" if len(var_value) > 8 else var_value
                print(f"--- zeabur_start.py: Env var {var_name} = {display_value} (Exists) ---")
            else:
                print(f"--- zeabur_start.py: Env var {var_name} = Not found ---")

        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            error_message = f"❌ 缺少必要的環境變數: {', '.join(missing_vars)}"
            print(f"--- zeabur_start.py: ERROR - {error_message} ---")
            logger.error(error_message)
            logger.error("請在 Zeabur 控制台設定環境變數")
            sys.exit(1)

        print("--- zeabur_start.py: Environment variables check passed ---")
        logger.info("✅ 環境變數檢查通過")

        print("--- zeabur_start.py: Attempting to import app.main:app ---")
        from app.main import app
        print("--- zeabur_start.py: Successfully imported app.main:app ---")

        import uvicorn
        print("--- zeabur_start.py: Attempting to run uvicorn ---")

        uvicorn.run(
            app,  # 直接傳遞 app 物件
            host="0.0.0.0",
            port=int(port),
            log_level="debug",
            access_log=True,
            workers=1
        )
        # uvicorn.run is blocking, so code below here won't run unless uvicorn exits
        print("--- zeabur_start.py: uvicorn.run called (should not reach here if uvicorn is blocking correctly) ---")

    except ImportError as e:
        error_msg = f"❌ 匯入模組失敗: {e}"
        print(f"--- zeabur_start.py: IMPORT ERROR - {error_msg} ---")
        logger.error(error_msg)
        logger.error("請檢查 requirements.txt 是否包含所有必要套件")
        sys.exit(1)
    except Exception as e:
        error_msg = f"❌ 啟動失敗: {e}"
        print(f"--- zeabur_start.py: GENERAL ERROR - {error_msg} ---")
        logger.error(error_msg)
        # Print traceback for general errors
        import traceback
        print("--- zeabur_start.py: Traceback --- ")
        traceback.print_exc()
        print("--- zeabur_start.py: End Traceback --- ")
        sys.exit(1)
    print("--- zeabur_start.py: main() function normally ended (should not happen if uvicorn is blocking) ---")

if __name__ == "__main__":
    print("--- zeabur_start.py: Script execution started (__main__) ---")
    main()
