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
import uvicorn

# 設定日誌基礎配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("zeabur_start") # 使用特定的 logger 名稱

print("--- zeabur_start.py: Script started ---")
logger.info("--- zeabur_start.py: Script started (logger) ---")

# 確保專案根目錄在 Python 路徑中
project_root = Path(__file__).resolve().parent # 使用 resolve() 獲取絕對路徑
sys.path.insert(0, str(project_root))
print(f"--- zeabur_start.py: sys.path[0] = {sys.path[0]} ---")
logger.info(f"--- zeabur_start.py: sys.path[0] = {sys.path[0]} (logger) ---")

port_str = os.getenv("PORT", "8080") # Zeabur 會提供 PORT
print(f"--- zeabur_start.py: PORT string from env: {port_str} ---")
logger.info(f"--- zeabur_start.py: PORT string from env: {port_str} (logger) ---")

try:
    port = int(port_str)
    print(f"--- zeabur_start.py: Effective PORT: {port} ---")
    logger.info(f"--- zeabur_start.py: Effective PORT: {port} (logger) ---")
except ValueError:
    print(f"--- zeabur_start.py: ERROR - Invalid PORT value: {port_str}. Defaulting to 8080 ---")
    logger.error(f"--- zeabur_start.py: ERROR - Invalid PORT value: {port_str}. Defaulting to 8080 (logger) ---")
    port = 8080

try:
    print("--- zeabur_start.py: Attempting to run uvicorn app.main:app ---")
    logger.info("--- zeabur_start.py: Attempting to run uvicorn app.main:app (logger) ---")
    uvicorn.run(
        "app.main:app", # 指向簡化後的 app/main.py 中的 app 實例
        host="0.0.0.0",
        port=port,
        log_level="debug", # 使用 debug 以獲取更詳細的 uvicorn 日誌
        access_log=True,
        workers=1 # Zeabur 建議
    )
except SystemExit as e: # Uvicorn 在某些情況下可能以 SystemExit 退出
    print(f"--- zeabur_start.py: Uvicorn exited with SystemExit: {e} ---")
    logger.info(f"--- zeabur_start.py: Uvicorn exited with SystemExit: {e} (logger) ---")
    # 根據 e.code 決定是否真的算錯誤
    if e.code != 0: # 非 0 的退出碼通常表示有問題
      raise # 重新拋出異常以便 Zeabur 知道啟動失敗
except Exception as e:
    print(f"--- zeabur_start.py: ERROR during uvicorn.run: {e} ---")
    logger.error(f"--- zeabur_start.py: ERROR during uvicorn.run: {e} (logger) ---")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("--- zeabur_start.py: Script ended (should ideally not be reached if uvicorn is blocking and running) ---")
logger.info("--- zeabur_start.py: Script ended (logger) ---")
