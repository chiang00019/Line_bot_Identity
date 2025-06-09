# 使用官方 Python 映像檔
FROM python:3.11-slim

# 設定環境變數，確保 Python 輸出不被緩衝，日誌能即時顯示
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /app

# 設定工作目錄
WORKDIR /app

# 1. 先安裝 uv（超快的 Python 依賴管理工具）
RUN pip install uv

# 2. 複製 lock file（和 requirements.txt，建議都帶著）
COPY requirements.txt .
COPY requirements.lock.txt .

# 3. 用 lock file 安裝依賴（**只需要這一步，會照 lock file 一模一樣還原所有依賴**）
RUN uv pip sync requirements.lock.txt

# 4. 複製專案所有檔案
COPY . .

# EXPOSE 8080 # 可以省略

# 5. 設定啟動命令
CMD ["python", "zeabur_start.py"]
