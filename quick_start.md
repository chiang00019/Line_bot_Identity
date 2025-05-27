# 🚀 Line Bot 快速設定指南

## 步驟 1: 取得 Channel Access Token

1. 前往 [Line Developers Console](https://developers.line.biz/)
2. 選擇您的 Channel (ID: 2007488515)
3. 進入 "Messaging API" 頁籤
4. 在 "Channel access token" 區域點擊 "Issue" 按鈕
5. 複製產生的 token

## 步驟 2: 建立環境變數檔案

建立 `.env` 檔案，內容如下：

```env
# Line Bot 設定
CHANNEL_ACCESS_TOKEN=您剛才取得的_Channel_Access_Token
CHANNEL_SECRET=7722bc67ef58e17456956cd4101b95af

# 應用程式設定
DEBUG=True
PORT=5000
```

## 步驟 3: 啟動應用程式

```bash
# 方法 1: 直接執行
python app/main.py

# 方法 2: 使用 uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload
```

## 步驟 4: 設定 Webhook URL

### 本地開發 (使用 ngrok)

1. 安裝 ngrok: https://ngrok.com/
2. 啟動 ngrok:
   ```bash
   ngrok http 5000
   ```
3. 複製 ngrok 提供的 HTTPS URL (例如: https://abc123.ngrok.io)
4. 在 Line Developers Console 填入:
   ```
   https://abc123.ngrok.io/callback
   ```

### 生產環境

如果您有自己的伺服器域名：
```
https://您的域名.com/callback
```

## 步驟 5: 測試設定

啟動後訪問以下 URL 測試：

- 健康檢查: `http://localhost:5000/health`
- API 文檔: `http://localhost:5000/docs`
- Webhook 測試: `http://localhost:5000/webhook/test`

## 🔧 重要提醒

1. **HTTPS 必要**: Line Webhook 要求使用 HTTPS
2. **Channel Secret**: 已從您的設定中取得 `7722bc67ef58e17456956cd4101b95af`
3. **Channel Access Token**: 需要您自行到 Line Developers Console 取得
4. **Webhook 啟用**: 記得在 Line Console 中啟用 Webhook 功能

## 💡 測試訊息

設定完成後，可以傳送以下訊息測試：

- `開始` - 顯示主選單
- `測試` - 測試基本功能
- `說明` - 顯示使用說明
