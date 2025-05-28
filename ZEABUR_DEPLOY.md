# 🚀 Zeabur 部署指南

## 📋 部署前準備

### 1. 確認檔案結構
確保你的專案包含以下核心檔案：
```
├── app/
│   ├── main.py           # FastAPI 主程式
│   ├── bot_handler.py    # Line Bot 處理器
│   ├── models.py         # 資料庫模型
│   └── services/         # 服務模組
├── config/
│   └── settings.py       # 配置設定
├── requirements.txt      # Python 依賴
├── zeabur.json          # Zeabur 配置
└── Dockerfile           # Docker 配置（可選）
```

### 2. 準備環境變數
參考 `zeabur_env_template.txt` 準備以下必要的環境變數：
- `CHANNEL_ACCESS_TOKEN` - Line Bot Channel Access Token
- `CHANNEL_SECRET` - Line Bot Channel Secret

## 🌐 部署步驟

### 步驟 1: 登入 Zeabur
1. 前往 [Zeabur 官網](https://zeabur.com/)
2. 使用 GitHub 帳號登入
3. 建立新專案

### 步驟 2: 連接 Git 倉庫
1. 在 Zeabur 控制台點選 "New Service"
2. 選擇 "Git Repository"
3. 選擇你的 Line Bot 專案倉庫
4. 選擇要部署的分支（通常是 `main` 或 `master`）

### 步驟 3: 配置服務
1. Zeabur 會自動偵測到這是一個 Python 專案
2. 確認建置指令：`pip install -r requirements.txt`
3. 確認啟動指令：`uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 步驟 4: 設定環境變數
在 Zeabur 服務設定中的 "Environment Variables" 頁面設定：

```bash
# 必要變數
CHANNEL_ACCESS_TOKEN=你的_Line_Bot_Channel_Access_Token
CHANNEL_SECRET=你的_Line_Bot_Channel_Secret

# 可選變數
DATABASE_URL=sqlite:///./game_bot.db
DEBUG_MODE=false
LOG_LEVEL=INFO
WEBHOOK_URL=https://你的應用名稱.zeabur.app/callback
```

### 步驟 5: 部署
1. 點擊 "Deploy" 按鈕
2. 等待建置完成（約 2-5 分鐘）
3. 部署成功後會獲得一個 URL，例如：`https://your-app-name.zeabur.app`

### 步驟 6: 設定 Line Bot Webhook
1. 前往 [Line Developers Console](https://developers.line.biz/)
2. 選擇你的 Bot 頻道
3. 在 "Messaging API" 頁面設定 Webhook URL：
   ```
   https://your-app-name.zeabur.app/callback
   ```
4. 啟用 Webhook
5. 測試 Webhook 連接

## 🔧 驗證部署

### 健康檢查
訪問以下 URL 確認服務正常：
- 首頁：`https://your-app-name.zeabur.app/`
- 健康檢查：`https://your-app-name.zeabur.app/health`
- API 文檔：`https://your-app-name.zeabur.app/docs`

### 測試 Line Bot
1. 將 Bot 加為好友
2. 傳送測試訊息
3. 檢查是否有正常回應

## 📊 監控與日誌

### 查看日誌
1. 在 Zeabur 控制台點選你的服務
2. 前往 "Logs" 頁面
3. 即時監控應用程式運行狀態

### 性能監控
- Zeabur 提供基本的 CPU、記憶體使用監控
- 可以查看請求次數和回應時間

## 🔄 更新部署

### 自動部署
- 推送程式碼到 GitHub 會自動觸發重新部署
- 建議使用 Git tag 管理版本

### 手動部署
1. 在 Zeabur 控制台點選 "Redeploy"
2. 選擇要部署的 commit

## ⚠️ 注意事項

### 資源限制
- Zeabur 免費方案有使用時間限制
- 建議升級到付費方案以獲得更穩定的服務

### 資料庫
- 預設使用 SQLite，資料會在重新部署時遺失
- 建議使用 Zeabur 的 PostgreSQL 服務作為正式資料庫

### 檔案儲存
- 上傳的檔案（如截圖）會在重新部署時遺失
- 建議使用雲端儲存服務（如 AWS S3）

### SSL 憑證
- Zeabur 自動提供 HTTPS
- Line Bot Webhook 要求必須使用 HTTPS

## 🛠️ 常見問題

### Q: 部署失敗怎麼辦？
A: 檢查建置日誌，常見原因：
- `requirements.txt` 格式錯誤
- Python 版本不相容
- 缺少必要檔案

### Q: Line Bot 無法接收訊息？
A: 檢查：
1. Webhook URL 是否正確設定
2. 環境變數是否正確設定
3. Line Bot 是否啟用 Webhook

### Q: 如何查看詳細錯誤？
A: 在 Zeabur 控制台的 Logs 頁面查看即時日誌

## 📞 技術支援

- [Zeabur 官方文檔](https://zeabur.com/docs)
- [Line Bot SDK 文檔](https://line.github.io/line-bot-sdk-python/)
- [FastAPI 文檔](https://fastapi.tiangolo.com/)

## 🎉 完成！

部署成功後，你的 Line Bot 就可以正常運作了！
記得定期檢查日誌和監控資料，確保服務穩定運行。
