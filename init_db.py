#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
資料庫初始化腳本
"""

import sys
import os
import logging
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from app.database import init_database, drop_all_tables, get_db_session
from app.models import SystemConfig
from config.settings import Config

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_directories():
    """建立必要的目錄"""
    directories = [
        Config.SCREENSHOT_DIR,
        Config.ZIP_OUTPUT_DIR,
        os.path.dirname(Config.LOG_FILE),
        './temp'
    ]

    for directory in directories:
        if directory:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"✅ 建立目錄: {directory}")

def setup_default_configs():
    """設置預設系統配置"""
    default_configs = [
        {
            'config_key': 'min_deposit_amount',
            'config_value': str(Config.MIN_TOP_UP_AMOUNT),
            'description': '最低充值金額 (NT$)',
            'is_active': True
        },
        {
            'config_key': 'max_deposit_amount',
            'config_value': str(Config.MAX_TOP_UP_AMOUNT),
            'description': '最高充值金額 (NT$)',
            'is_active': True
        },
        {
            'config_key': 'token_exchange_rate',
            'config_value': str(Config.TOKEN_EXCHANGE_RATE),
            'description': 'Token 兌換比率 (1 NT$ = ? Token)',
            'is_active': True
        },
        {
            'config_key': 'bank_account_info',
            'config_value': '''銀行：台灣銀行
帳號：123-456-789-000
戶名：線上遊戲儲值系統
備註：轉帳時請註明群組識別碼''',
            'description': '收款銀行帳戶資訊',
            'is_active': True
        },
        {
            'config_key': 'auto_email_check_interval',
            'config_value': '300',  # 5分鐘
            'description': 'Email 自動檢查間隔 (秒)',
            'is_active': True
        },
        {
            'config_key': 'razer_max_retry_count',
            'config_value': '3',
            'description': 'Razer 儲值最大重試次數',
            'is_active': True
        },
        {
            'config_key': 'screenshot_quality',
            'config_value': '90',
            'description': '截圖品質 (1-100)',
            'is_active': True
        }
    ]

    try:
        with get_db_session() as db:
            for config_data in default_configs:
                existing = db.query(SystemConfig).filter_by(
                    config_key=config_data['config_key']
                ).first()

                if not existing:
                    config = SystemConfig(**config_data)
                    db.add(config)
                    logger.info(f"✅ 建立預設配置: {config_data['config_key']} = {config_data['config_value']}")
                else:
                    logger.info(f"⚠️  配置已存在: {config_data['config_key']}")

            db.commit()
            logger.info("✅ 預設配置設置完成")

    except Exception as e:
        logger.error(f"❌ 設置預設配置失敗: {str(e)}")
        return False

    return True

def verify_database():
    """驗證資料庫是否正確建立"""
    try:
        with get_db_session() as db:
            from app.models import Group, User, GroupMember, TokenLog, EmailLog, RazerLog, SystemConfig

            # 檢查所有資料表是否存在
            tables_to_check = [
                (Group, 'groups'),
                (User, 'users'),
                (GroupMember, 'group_members'),
                (TokenLog, 'token_logs'),
                (EmailLog, 'email_logs'),
                (RazerLog, 'razer_logs'),
                (SystemConfig, 'system_config')
            ]

            for model_class, table_name in tables_to_check:
                try:
                    count = db.query(model_class).count()
                    logger.info(f"✅ 資料表 {table_name}: {count} 筆記錄")
                except Exception as e:
                    logger.error(f"❌ 資料表 {table_name} 檢查失敗: {str(e)}")
                    return False

            logger.info("✅ 資料庫驗證完成")
            return True

    except Exception as e:
        logger.error(f"❌ 資料庫驗證失敗: {str(e)}")
        return False

def main():
    """主要初始化函數"""
    logger.info("🚀 開始資料庫初始化程序...")

    try:
        # 1. 建立必要目錄
        logger.info("📁 建立必要目錄...")
        create_directories()

        # 2. 檢查配置
        logger.info("⚙️  檢查配置設定...")
        if not Config.validate_config():
            logger.warning("⚠️  配置驗證失敗，但繼續初始化資料庫...")
        else:
            logger.info("✅ 配置檢查通過")

        # 3. 初始化資料庫
        logger.info("🗄️  建立資料庫資料表...")
        init_database()
        logger.info("✅ 資料表建立完成")

        # 4. 設置預設配置
        logger.info("🔧 設置預設系統配置...")
        if not setup_default_configs():
            logger.warning("⚠️  預設配置設置部分失敗，但資料庫初始化繼續...")

        # 5. 驗證資料庫
        logger.info("🔍 驗證資料庫完整性...")
        if not verify_database():
            logger.error("❌ 資料庫驗證失敗")
            return 1

        # 6. 顯示初始化完成資訊
        logger.info("🎉 資料庫初始化完成！")
        print("\n" + "="*60)
        print("🎉 Line Bot Token管理系統 - 資料庫初始化完成")
        print("="*60)
        print("✅ 資料庫資料表已建立")
        print("✅ 預設配置已設置")
        print("✅ 目錄結構已建立")
        print()
        print("📋 後續步驟:")
        print("1. 設定環境變數 (.env 檔案)")
        print("2. 配置 Line Bot Channel Access Token")
        print("3. 設定 Email IMAP/SMTP 帳戶")
        print("4. 測試 Line Bot 基本功能")
        print("5. 配置 Razer 儲值相關設定")
        print()
        print("🚀 準備啟動服務器:")
        print("   python run.py")
        print("="*60)

        return 0

    except Exception as e:
        logger.error(f"❌ 資料庫初始化失敗: {str(e)}")
        print(f"\n❌ 初始化失敗: {str(e)}")
        print("\n🔧 故障排除建議:")
        print("1. 檢查資料庫連線設定")
        print("2. 確認 SQLAlchemy 版本相容性")
        print("3. 檢查檔案權限")
        print("4. 查看詳細錯誤日誌")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
