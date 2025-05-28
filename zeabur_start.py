#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import time
from pathlib import Path
import logging
import uvicorn

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("zeabur_start")

print("--- zeabur_start.py: Script started (v2) ---") # 版本標記
logger.info("--- zeabur_start.py: Script started (v2) (logger) ---")

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))
print(f"--- zeabur_start.py: sys.path[0] = {sys.path[0]} ---")

port_str = os.getenv("PORT", "8080")
print(f"--- zeabur_start.py: PORT string from env: {port_str} ---")

try:
    port = int(port_str)
except ValueError:
    print(f"--- zeabur_start.py: ERROR - Invalid PORT value: {port_str}. Defaulting to 8080 ---")
    port = 8080
print(f"--- zeabur_start.py: Effective PORT: {port} ---")

# 打印關鍵環境變數
token = os.getenv("CHANNEL_ACCESS_TOKEN")
secret = os.getenv("CHANNEL_SECRET")
print(f"--- zeabur_start.py: CHANNEL_ACCESS_TOKEN exists: {bool(token)} ---")
print(f"--- zeabur_start.py: CHANNEL_SECRET exists: {bool(secret)} ---")
if not token or not secret:
    print("--- zeabur_start.py: CRITICAL ERROR - Missing Line Bot credentials! ---")
    # sys.exit(1) # 暫時不退出，看 uvicorn 是否能啟動

try:
    print("--- zeabur_start.py: Attempting to import app from app.main ---")
    from app.main import app # 直接導入 app 實例
    print("--- zeabur_start.py: Successfully imported app from app.main ---")

    print(f"--- zeabur_start.py: Attempting to run uvicorn with imported app object, host 0.0.0.0, port {port} ---")
    logger.info(f"--- zeabur_start.py: Attempting to run uvicorn with imported app object, host 0.0.0.0, port {port} (logger) ---")

    uvicorn.run(
        app, # 直接傳遞 app 物件
        host="0.0.0.0",
        port=port,
        log_level="debug",
        access_log=True,
        workers=1
    )
except SystemExit as e:
    print(f"--- zeabur_start.py: Uvicorn exited with SystemExit code: {e.code} ---")
    logger.info(f"--- zeabur_start.py: Uvicorn exited with SystemExit code: {e.code} (logger) ---")
    if e.code != 0:
      sys.exit(e.code) # 如果 uvicorn 因錯誤退出，腳本也以錯誤碼退出
except ImportError as e_import:
    print(f"--- zeabur_start.py: IMPORT ERROR: {e_import} ---")
    logger.error(f"--- zeabur_start.py: IMPORT ERROR: {e_import} (logger) ---")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e_general:
    print(f"--- zeabur_start.py: GENERAL ERROR during uvicorn.run: {e_general} ---")
    logger.error(f"--- zeabur_start.py: GENERAL ERROR during uvicorn.run: {e_general} (logger) ---")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("--- zeabur_start.py: Script ended AFTER uvicorn.run (SHOULD NOT BE REACHED if uvicorn is blocking) ---")
logger.info("--- zeabur_start.py: Script ended AFTER uvicorn.run (logger) ---")
