# 使用官方 Python 映像檔
FROM python:3.11-slim

# 設定環境變數，確保 Python 輸出不被緩衝，日誌能即時顯示
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /app

# 設定工作目錄
WORKDIR /app

# 1. 複製 requirements.txt
COPY requirements.txt .

# 2. 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 3. 安裝 Playwright 瀏覽器
RUN playwright install chromium

# 4. 複製專案所有檔案
COPY . .

# EXPOSE 8080 # 可以省略

# 5. 設定啟動命令
CMD ["python", "zeabur_start.py"]
