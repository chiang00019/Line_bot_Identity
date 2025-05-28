#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zeabur 專用啟動檔案
簡化的 Line Bot 啟動器，專門為 Zeabur 平台優化
"""

import os
import sys
import time # 新增 time 模組
from pathlib import Path

print(f"--- zeabur_start.py: TOP OF SCRIPT --- Python version: {sys.version} ---")

# 確保專案根目錄在 Python 路徑中
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))
print(f"--- zeabur_start.py: sys.path[0] = {sys.path[0]} ---")

port_str = os.getenv("PORT", "8080")
print(f"--- zeabur_start.py: PORT string from env: {port_str} ---")

# 打印所有環境變數，檢查關鍵變數是否存在
print("--- zeabur_start.py: All Environment Variables ---")
for key, value in os.environ.items():
    if "TOKEN" in key.upper() or "SECRET" in key.upper(): # 部分遮蔽敏感資訊
        display_value = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else value
        print(f"--- zeabur_start.py: ENV: {key} = {display_value} ---")
    else:
        print(f"--- zeabur_start.py: ENV: {key} = {value} ---")
print("--- zeabur_start.py: End of Environment Variables ---")

# 檢查關鍵環境變數
token = os.getenv("CHANNEL_ACCESS_TOKEN")
secret = os.getenv("CHANNEL_SECRET")
if not token:
    print("--- zeabur_start.py: ERROR - CHANNEL_ACCESS_TOKEN is MISSING ---")
if not secret:
    print("--- zeabur_start.py: ERROR - CHANNEL_SECRET is MISSING ---")

print("--- zeabur_start.py: This is a minimal test. Script will now exit. ---")
# 為了讓日誌有時間被收集，可以短暫睡眠
# time.sleep(5) # 如果日誌還是看不到，可以試試這個
# sys.exit(0) # 正常退出，看看日誌是否顯示
# 如果上面被註解，腳本會執行完畢並退出，容器可能被視為"成功"執行完畢但沒做任何事
# Zeabur 可能期望一個長時間運行的進程，如果腳本快速退出，也可能導致 backoff
# 讓我們故意引發一個異常，看看 Traceback 是否會出現在日誌中
# raise Exception("--- zeabur_start.py: This is a deliberate test exception to check logging. ---")
# 或者，讓它保持運行一段時間
print("--- zeabur_start.py: Minimal test script will keep running for 60 seconds to check logs... ---")
time.sleep(60)
print("--- zeabur_start.py: Minimal test script finished running. ---")
