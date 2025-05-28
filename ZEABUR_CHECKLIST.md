# ✅ Zeabur 部署檢查清單

## 🔍 部署前檢查

### 📁 檔案準備
- [ ] `app/main.py` - 主程式檔案存在
- [ ] `requirements.txt` - 依賴套件清單完整
- [ ] `zeabur.json` - Zeabur 配置檔案存在
- [ ] `zeabur_start.py` - 啟動檔案存在
- [ ] `config/settings.py` - 配置檔案存在

### 🔐 Line Bot 設定
- [ ] 已建立 Line Bot Channel
- [ ] 取得 Channel Access Token
- [ ] 取得 Channel Secret
- [ ] Messaging API 已啟用

### 📚 Git 倉庫
- [ ] 程式碼已推送到 GitHub
- [ ] 倉庫設為 Public（或確保 Zeabur 有存取權限）
- [ ] 選擇正確的部署分支

## 🚀 Zeabur 部署步驟

### 1. 建立服務
- [ ] 登入 Zeabur 控制台
- [ ] 建立新專案
- [ ] 選擇 Git Repository
- [ ] 連接你的 GitHub 倉庫

### 2. 設定環境變數
在 Zeabur 控制台設定以下環境變數：

#### 必要變數
- [ ] `CHANNEL_ACCESS_TOKEN` = `你的_Channel_Access_Token`
- [ ] `CHANNEL_SECRET` = `你的_Channel_Secret`

#### 可選變數
- [ ] `DATABASE_URL` = `sqlite:///./game_bot.db`
- [ ] `DEBUG_MODE` = `false`
- [ ] `LOG_LEVEL` = `INFO`

### 3. 部署設定
- [ ] 確認建置指令：`pip install --no-cache-dir -r requirements.txt`
- [ ] 確認啟動指令：`python zeabur_start.py`
- [ ] 確認健康檢查路徑：`/health`

### 4. 執行部署
- [ ] 點擊 Deploy 按鈕
- [ ] 等待建置完成（約 2-5 分鐘）
- [ ] 確認部署狀態為 "Running"

## 🔧 部署後驗證

### 服務檢查
- [ ] 訪問應用程式 URL（如：`https://your-app.zeabur.app`）
- [ ] 檢查健康檢查端點：`/health`
- [ ] 檢查 API 文檔：`/docs`
- [ ] 查看 Zeabur 日誌確認無錯誤

### Line Bot 設定
- [ ] 在 Line Developers Console 設定 Webhook URL
  ```
  https://your-app-name.zeabur.app/callback
  ```
- [ ] 啟用 Webhook
- [ ] 測試 Webhook 連接（應顯示成功）

### 功能測試
- [ ] 將 Bot 加為好友
- [ ] 傳送測試訊息：`你好`
- [ ] 確認 Bot 有正常回應
- [ ] 測試基本指令（如 `/help`）

## 📊 監控設定

### 日誌監控
- [ ] 在 Zeabur 控制台查看即時日誌
- [ ] 確認沒有錯誤訊息
- [ ] 監控請求處理狀況

### 效能監控
- [ ] 檢查 CPU 使用率
- [ ] 檢查記憶體使用率
- [ ] 監控回應時間

## 🔄 持續維護

### 自動部署
- [ ] 確認 Git 推送會觸發自動部署
- [ ] 測試 hot-reload 功能

### 備份
- [ ] 定期備份資料庫（如有使用）
- [ ] 備份重要配置

### 更新
- [ ] 定期更新依賴套件
- [ ] 關注 Zeabur 平台更新

## ⚠️ 常見問題檢查

### 如果部署失敗
- [ ] 檢查 `requirements.txt` 格式
- [ ] 確認 Python 版本相容性
- [ ] 查看建置日誌中的錯誤訊息

### 如果 Line Bot 無回應
- [ ] 確認 Webhook URL 設定正確
- [ ] 檢查環境變數設定
- [ ] 查看應用程式日誌
- [ ] 確認 Line Bot API 憑證正確

### 如果服務無法存取
- [ ] 確認服務狀態為 "Running"
- [ ] 檢查域名設定
- [ ] 確認防火牆設定

## 🎉 部署完成確認

當所有項目都勾選完成後，你的 Line Bot 就成功部署到 Zeabur 了！

### 最終測試
1. 🤖 Line Bot 正常回應訊息
2. 🌐 網頁服務可正常存取
3. 📊 監控面板顯示服務健康
4. 📝 日誌沒有錯誤訊息

---

**📞 需要協助？**
- 查看 `ZEABUR_DEPLOY.md` 了解詳細步驟
- 檢查 Zeabur 官方文檔
- 查看專案 README.md
