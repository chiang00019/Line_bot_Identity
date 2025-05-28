# 使用官方 Python 映像檔
FROM python:3.11-slim

# 設定環境變數，確保 Python 輸出不被緩衝，日誌能即時顯示
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /app

# 設定工作目錄
WORKDIR /app

# 複製依賴定義檔案
COPY requirements.txt .

# 安裝依賴
# 使用 --prefer-binary 嘗試避免編譯問題，--no-cache-dir 減少映像檔大小
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# 複製專案中的所有檔案到工作目錄
# 注意：確保 .dockerignore 檔案有正確設定，以排除不必要的檔案
COPY . .

# 暴露的端口將由 zeabur_start.py 內部讀取的 $PORT 環境變數決定
# EXPOSE 8080 # 可以不寫，因為 Zeabur 會處理端口映射

# 設定啟動命令，使用我們為 Zeabur 準備的啟動腳本
CMD ["python", "zeabur_start.py"]
