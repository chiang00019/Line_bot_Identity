#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FastAPI 應用程式啟動腳本
"""

import uvicorn
from app.main import app

if __name__ == "__main__":
    # 啟動 FastAPI 應用程式
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info",
        access_log=True
    )
