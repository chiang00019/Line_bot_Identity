#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Line Bot Webhook 測試腳本

此腳本用於測試 Line Bot Webhook 端點是否正常運作
"""

import requests
import json
import hashlib
import hmac
import base64
from datetime import datetime

# 測試設定
WEBHOOK_URL = "http://localhost:5000/callback"
HEALTH_URL = "http://localhost:5000/health"
TEST_URL = "http://localhost:5000/webhook/test"

# 模擬的 Line Bot 設定（僅用於測試）
TEST_CHANNEL_SECRET = "test_channel_secret"

def create_signature(body: str, secret: str) -> str:
    """創建 Line Bot 簽名"""
    hash = hmac.new(secret.encode('utf-8'), body.encode('utf-8'), hashlib.sha256).digest()
    return base64.b64encode(hash).decode('utf-8')

def test_health_check():
    """測試健康檢查端點"""
    print("🔍 測試健康檢查端點...")
    try:
        response = requests.get(HEALTH_URL, timeout=10)
        print(f"狀態碼: {response.status_code}")
        print(f"回應: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 健康檢查失敗: {e}")
        return False

def test_webhook_endpoint():
    """測試 Webhook 測試端點"""
    print("\n🔍 測試 Webhook 測試端點...")
    try:
        response = requests.get(TEST_URL, timeout=10)
        print(f"狀態碼: {response.status_code}")
        print(f"回應: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Webhook 測試端點失敗: {e}")
        return False

def test_text_message_webhook():
    """測試文字訊息 Webhook"""
    print("\n🔍 測試文字訊息 Webhook...")

    # 模擬 Line 文字訊息事件
    mock_event = {
        "events": [
            {
                "type": "message",
                "message": {
                    "type": "text",
                    "id": "test_message_id",
                    "text": "測試訊息"
                },
                "timestamp": int(datetime.now().timestamp() * 1000),
                "source": {
                    "type": "user",
                    "userId": "test_user_id"
                },
                "replyToken": "test_reply_token"
            }
        ],
        "destination": "test_destination"
    }

    body = json.dumps(mock_event, separators=(',', ':'))
    signature = create_signature(body, TEST_CHANNEL_SECRET)

    headers = {
        'Content-Type': 'application/json',
        'X-Line-Signature': signature
    }

    try:
        response = requests.post(WEBHOOK_URL, data=body, headers=headers, timeout=10)
        print(f"狀態碼: {response.status_code}")

        if response.status_code == 200:
            print(f"✅ 成功回應: {response.json()}")
            return True
        else:
            print(f"❌ 錯誤回應: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Webhook 測試失敗: {e}")
        return False

def test_follow_event_webhook():
    """測試追蹤事件 Webhook"""
    print("\n🔍 測試追蹤事件 Webhook...")

    # 模擬 Line 追蹤事件
    mock_event = {
        "events": [
            {
                "type": "follow",
                "timestamp": int(datetime.now().timestamp() * 1000),
                "source": {
                    "type": "user",
                    "userId": "test_user_id"
                },
                "replyToken": "test_reply_token"
            }
        ],
        "destination": "test_destination"
    }

    body = json.dumps(mock_event, separators=(',', ':'))
    signature = create_signature(body, TEST_CHANNEL_SECRET)

    headers = {
        'Content-Type': 'application/json',
        'X-Line-Signature': signature
    }

    try:
        response = requests.post(WEBHOOK_URL, data=body, headers=headers, timeout=10)
        print(f"狀態碼: {response.status_code}")

        if response.status_code == 200:
            print(f"✅ 成功回應: {response.json()}")
            return True
        else:
            print(f"❌ 錯誤回應: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 追蹤事件測試失敗: {e}")
        return False

def test_invalid_signature():
    """測試無效簽名"""
    print("\n🔍 測試無效簽名...")

    mock_event = {
        "events": [
            {
                "type": "message",
                "message": {
                    "type": "text",
                    "id": "test_message_id",
                    "text": "測試訊息"
                },
                "timestamp": int(datetime.now().timestamp() * 1000),
                "source": {
                    "type": "user",
                    "userId": "test_user_id"
                },
                "replyToken": "test_reply_token"
            }
        ]
    }

    body = json.dumps(mock_event)

    headers = {
        'Content-Type': 'application/json',
        'X-Line-Signature': 'invalid_signature'
    }

    try:
        response = requests.post(WEBHOOK_URL, data=body, headers=headers, timeout=10)
        print(f"狀態碼: {response.status_code}")

        if response.status_code == 400:
            print("✅ 正確拒絕無效簽名")
            return True
        else:
            print(f"❌ 未正確處理無效簽名: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 無效簽名測試失敗: {e}")
        return False

def main():
    """執行所有測試"""
    print("🚀 開始 Line Bot Webhook 測試")
    print("=" * 50)

    test_results = []

    # 執行各項測試
    test_results.append(("健康檢查", test_health_check()))
    test_results.append(("Webhook 測試端點", test_webhook_endpoint()))
    test_results.append(("文字訊息 Webhook", test_text_message_webhook()))
    test_results.append(("追蹤事件 Webhook", test_follow_event_webhook()))
    test_results.append(("無效簽名測試", test_invalid_signature()))

    # 顯示測試結果
    print("\n" + "=" * 50)
    print("📊 測試結果摘要")
    print("=" * 50)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\n通過率: {passed}/{total} ({passed/total*100:.1f}%)")

    if passed == total:
        print("🎉 所有測試都通過了！")
    else:
        print("⚠️ 有一些測試失敗，請檢查應用程式設定。")

    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
