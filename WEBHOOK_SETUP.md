# Line Bot Webhook 設定指南

本文檔詳細說明如何設定 Line Bot Webhook 來接收 Line 平台的訊息。

## 🔧 Webhook 端點設定

### 主要 Webhook 端點

- **URL**: `https://yourdomain.com/callback`
- **方法**: `POST`
- **內容類型**: `application/json`

### 支援的事件類型

我們的 FastAPI 應用程式支援以下 Line 事件：

#### 📨 訊息事件 (MessageEvent)
- **文字訊息 (TextMessage)**: 用戶發送的文字內容
- **圖片訊息 (ImageMessage)**: 用戶上傳的圖片
- **位置訊息 (LocationMessage)**: 用戶分享的位置資訊
- **貼圖訊息 (StickerMessage)**: 用戶發送的 Line 貼圖

#### 🔄 互動事件
- **Postback 事件**: 來自按鈕或選單的互動
- **追蹤事件 (FollowEvent)**: 用戶開始追蹤 Bot
- **取消追蹤事件 (UnfollowEvent)**: 用戶取消追蹤 Bot

#### 👥 群組事件
- **加入群組事件 (JoinEvent)**: Bot 被加入群組
- **離開群組事件 (LeaveEvent)**: Bot 被移出群組

## 🚀 快速設定步驟

### 1. Line Developers Console 設定

1. 登入 [Line Developers Console](https://developers.line.biz/)
2. 建立新的 Messaging API 頻道
3. 取得以下資訊：
   - **Channel Access Token**
   - **Channel Secret**

### 2. 環境變數設定

編輯您的 `.env` 檔案：

```env
# Line Bot 設定
CHANNEL_ACCESS_TOKEN=你的_channel_access_token
CHANNEL_SECRET=你的_channel_secret
```

### 3. Webhook URL 設定

在 Line Developers Console 中設定 Webhook URL：

```
https://yourdomain.com/callback
```

### 4. 啟動應用程式

```bash
# 開發環境
python run.py

# 或使用 uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload
```

## 📋 Webhook 驗證

### 測試 Webhook 連接

1. **健康檢查**:
   ```
   GET https://yourdomain.com/health
   ```

2. **Webhook 測試**:
   ```
   GET https://yourdomain.com/webhook/test
   ```

### 預期回應

健康檢查回應：
```json
{
  "status": "healthy",
  "service": "game-automation-linebot",
  "version": "1.0.0",
  "line_bot_connected": true
}
```

Webhook 測試回應：
```json
{
  "status": "ok",
  "message": "Webhook endpoint is working",
  "webhook_url": "/callback",
  "supported_events": [
    "TextMessage",
    "ImageMessage",
    "LocationMessage",
    "StickerMessage",
    "PostbackEvent",
    "FollowEvent",
    "UnfollowEvent",
    "JoinEvent",
    "LeaveEvent"
  ]
}
```

## 🔒 安全設定

### Signature 驗證

我們的 Webhook 會自動驗證來自 Line 的請求簽名：

```python
# 自動處理 X-Line-Signature header 驗證
signature = request.headers.get('X-Line-Signature')
handler.handle(body_text, signature)
```

### 錯誤處理

- **400 Bad Request**: 缺少簽名或簽名無效
- **500 Internal Server Error**: 處理事件時發生錯誤

## 📊 監控和日誌

### 日誌記錄

應用程式會記錄以下資訊：

- 收到的 Webhook 請求
- 處理的事件類型和用戶 ID
- 錯誤和異常資訊

### 日誌範例

```
[2024-05-28 12:00:00] INFO: 收到 Line Webhook 請求，大小: 156 bytes
[2024-05-28 12:00:00] INFO: 收到用戶 U1234567890 的文字訊息: 開始
[2024-05-28 12:00:00] INFO: Line Webhook 事件處理成功
```

## 🐛 故障排除

### 常見問題

1. **Webhook 無法接收訊息**
   - 檢查 Webhook URL 是否可從外部訪問
   - 確認 HTTPS 設定正確
   - 驗證 Channel Secret 和 Access Token

2. **簽名驗證失敗**
   - 檢查 Channel Secret 是否正確
   - 確認請求 body 沒有被修改

3. **事件處理錯誤**
   - 查看應用程式日誌
   - 檢查事件處理器的實作

### 測試命令

使用 ngrok 進行本地測試：

```bash
# 安裝 ngrok
ngrok http 5000

# 使用提供的 HTTPS URL 作為 Webhook URL
# 例如: https://abc123.ngrok.io/callback
```

## 📚 進階設定

### 自定義事件處理

要添加新的事件處理器：

```python
@handler.add(EventType)
def handle_custom_event(event):
    # 您的處理邏輯
    pass
```

### 非同步處理

所有 Webhook 處理都是非同步的，確保高效能：

```python
@app.post("/callback")
async def line_webhook(request: Request):
    # 非同步處理邏輯
    pass
```

## 📞 支援

如果遇到問題，請：

1. 檢查日誌檔案: `./logs/app.log`
2. 查看 API 文檔: `http://localhost:5000/docs`
3. 測試健康檢查: `http://localhost:5000/health`

---

更多資訊請參考 [Line Bot SDK 文檔](https://developers.line.biz/en/docs/)。
