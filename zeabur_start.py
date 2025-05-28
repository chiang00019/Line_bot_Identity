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
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """主啟動函數"""
    try:
        # 顯示啟動資訊
        port = os.getenv("PORT", "5000")
        logger.info("🚀 啟動 Line Bot Token 管理系統")
        logger.info(f"📦 部署平台: Zeabur")
        logger.info(f"🌐 服務端口: {port}")

        # 檢查必要的環境變數
        required_vars = ["CHANNEL_ACCESS_TOKEN", "CHANNEL_SECRET"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            logger.error(f"❌ 缺少必要的環境變數: {', '.join(missing_vars)}")
            logger.error("請在 Zeabur 控制台設定環境變數")
            sys.exit(1)

        logger.info("✅ 環境變數檢查通過")

        # 匯入並啟動應用程式
        from app.main import app
        import uvicorn

        # Zeabur 專用配置
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=int(port),
            log_level="info",
            access_log=True,
            workers=1  # Zeabur 建議使用單一 worker
        )

    except ImportError as e:
        logger.error(f"❌ 匯入模組失敗: {e}")
        logger.error("請檢查 requirements.txt 是否包含所有必要套件")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 啟動失敗: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
