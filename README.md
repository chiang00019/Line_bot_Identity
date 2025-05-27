# 遊戲自動化儲值 Line Bot

一個基於 FastAPI 和 Line Bot 的遊戲自動化儲值系統，支援 Razer Gold 支付和自動化操作。

## 功能特色

- ⚡ **FastAPI 框架**: 高效能異步 Web 框架
- 🤖 **Line Bot 整合**: 完整的 Line Bot 介面
- 💰 **自動化儲值**: 支援多種遊戲平台自動儲值
- 💳 **Razer Gold 支付**: 整合 Razer Gold 支付系統
- 📊 **餘額管理**: 即時查詢和管理代幣餘額
- 📧 **通知系統**: 異步電子郵件通知功能
- 🔒 **安全加密**: 用戶資料安全加密存儲
- 📸 **截圖記錄**: 自動化過程截圖記錄
- 📈 **交易記錄**: 完整的交易歷史追蹤
- 📚 **自動化 API 文檔**: 內建 Swagger UI

## 專案結構

```
line_bot_project/
├── app/                   # 主要應用程式程式碼
│   ├── __init__.py
│   ├── main.py            # 應用程式進入點 (FastAPI app)
│   ├── bot_handler.py     # Line Bot 訊息處理邏輯
│   ├── models.py          # 資料庫模型
│   ├── services/          # 業務邏輯模組
│   │   ├── __init__.py
│   │   ├── token_service.py      # 代幣服務
│   │   ├── email_service.py      # 郵件服務
│   │   ├── razer_service.py      # Razer 支付服務
│   │   └── automation_service.py # 自動化服務
│   ├── utils/             # 工具函式
│   │   ├── __init__.py
│   │   └── helpers.py
│   └── templates/         # HTML 樣板（如需要）
├── tests/                 # 測試案例
│   └── __init__.py
├── config/                # 設定檔
│   ├── __init__.py
│   └── settings.py
├── .env.example           # 環境變數範例
├── requirements.txt       # Python 依賴套件列表
├── Dockerfile             # Docker 部署設定
└── README.md              # 專案說明
```

## 安裝指南

### 1. 環境需求

- Python 3.8+
- FastAPI 和 Uvicorn
- Chrome 瀏覽器（用於自動化）
- ChromeDriver

### 2. 安裝相依套件

```bash
pip install -r requirements.txt
```

### 3. 環境設定

1. 複製環境變數範例檔案：
```bash
cp .env.example .env
```

2. 編輯 `.env` 檔案，填入您的設定：

```env
# Line Bot 設定
CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here
CHANNEL_SECRET=your_line_channel_secret_here

# 其他設定...
```

### 4. 資料庫初始化

```bash
# 使用 Python 建立資料庫表格
python -c "from app.models import Base; from sqlalchemy import create_engine; from config.settings import Config; engine = create_engine(Config.DATABASE_URL); Base.metadata.create_all(engine)"
```

## 使用方法

### 啟動應用程式

開發環境啟動：
```bash
# 方法 1: 直接執行主檔案
python app/main.py

# 方法 2: 使用 uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload

# 方法 3: 使用啟動腳本
python run.py
```

伺服器將在 `http://localhost:5000` 啟動。

API 文檔將在以下位置可用：
- Swagger UI: `http://localhost:5000/docs`
- ReDoc: `http://localhost:5000/redoc`

### Line Bot 設定

1. 在 Line Developers Console 建立 Messaging API 頻道
2. 取得 Channel Access Token 和 Channel Secret
3. 設定 Webhook URL: `https://yourdomain.com/callback`
4. 將 Token 和 Secret 添加到 `.env` 檔案

### 可用指令

用戶可以透過 Line Bot 使用以下指令：

- `開始` 或 `start` - 顯示主選單
- `查詢餘額` - 查看當前代幣餘額
- `儲值` - 開始自動化儲值流程
- `設定` - 配置帳號和支付設定
- `說明` - 顯示說明訊息

## API 文檔

### 主要端點

- `GET /` - 首頁（HTML）
- `GET /health` - 健康檢查
- `POST /callback` - Line Bot Webhook
- `GET /docs` - Swagger API 文檔
- `GET /redoc` - ReDoc API 文檔

### 支付回調

- `POST /payment/callback` - Razer 支付回調
- `GET /payment/return` - 支付完成返回頁面

## 配置選項

主要配置選項在 `config/settings.py` 中：

```python
class Config:
    # Line Bot 設定
    CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN', '')
    CHANNEL_SECRET = os.getenv('CHANNEL_SECRET', '')

    # 資料庫設定
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///game_bot.db')

    # 更多設定...
```

## 開發指南

### 程式碼風格

使用 Black 進行程式碼格式化：

```bash
black app/ tests/ config/
```

### 執行測試

```bash
pytest tests/
```

### 靜態檢查

```bash
flake8 app/
mypy app/
```

## 部署

### Docker 部署

```bash
docker build -t game-bot .
docker run -p 5000:5000 --env-file .env game-bot
```

### 生產環境

使用 Uvicorn 啟動（推薦）：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 5000 --workers 4
```

或使用 Gunicorn + Uvicorn workers：

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:5000
```

## 安全注意事項

1. **環境變數**: 絕不要將 `.env` 檔案提交到版本控制
2. **HTTPS**: 生產環境務必使用 HTTPS
3. **資料加密**: 敏感資料已使用 Fernet 加密
4. **密碼哈希**: 使用 PBKDF2 進行密碼哈希

## 故障排除

### 常見問題

1. **Line Bot 無法接收訊息**
   - 檢查 Webhook URL 是否正確
   - 確認 Channel Secret 和 Access Token 正確

2. **自動化失敗**
   - 檢查 ChromeDriver 路徑
   - 確認螢幕解析度設定

3. **支付回調失敗**
   - 檢查 Razer 設定
   - 驗證回調 URL 可訪問性

### 日誌檔案

查看日誌檔案以獲取詳細錯誤資訊：

```bash
tail -f logs/app.log
```

## 貢獻指南

1. Fork 此專案
2. 建立功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交變更 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request

## 授權條款

此專案使用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 檔案。

## 聯絡資訊

如有任何問題或建議，請聯繫：

- 電子郵件: developer@example.com
- GitHub Issues: [專案 Issues 頁面](https://github.com/yourusername/game-bot/issues)

## 更新日誌

### v1.0.0 (2024-05-28)
- 初始版本發布
- 基本 Line Bot 功能
- Razer Gold 支付整合
- 自動化儲值功能
- 用戶餘額管理
- 電子郵件通知系統
