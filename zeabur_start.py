# app/main.py (極度簡化版 - 確認內容是這個)
from fastapi import FastAPI
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("app.main")

print("--- app/main.py: Script started, imports successful ---")
logger.info("--- app/main.py: Script started, imports successful (logger) ---")

app = FastAPI(title="Minimal Test App")
print("--- app/main.py: FastAPI app instance created ---")
logger.info("--- app/main.py: FastAPI app instance created (logger) ---")

@app.on_event("startup")
async def startup_event():
    print("--- app/main.py: Application startup event triggered ---")
    logger.info("--- app/main.py: Application startup event triggered (logger) ---")

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

@app.post("/callback")
def callback_placeholder():
    print("--- app/main.py: POST to /callback received (placeholder) ---")
    logger.info("--- app/main.py: POST to /callback received (placeholder) (logger) ---")
    return {"status": "ok"}

print("--- app/main.py: End of file, app instance and routes defined ---")
logger.info("--- app/main.py: End of file, app instance and routes defined (logger) ---")
