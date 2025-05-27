# -*- coding: utf-8 -*-
"""
應用程式設定檔案
"""

import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

class Config:
    """應用程式配置類別"""

    # === 基本設定 ===
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

    # === Line Bot 設定 ===
    CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN', '')
    CHANNEL_SECRET = os.getenv('CHANNEL_SECRET', '')

    # === 資料庫設定 ===
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///game_bot.db')

    # === 加密設定 ===
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', 'your-encryption-key-32-characters!')

    # === 郵件設定 (SMTP - 發送郵件) ===
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    FROM_EMAIL = os.getenv('FROM_EMAIL', 'noreply@gamebot.com')

    # === 郵件設定 (IMAP - 接收郵件) ===
    IMAP_SERVER = os.getenv('IMAP_SERVER', 'imap.gmail.com')
    IMAP_PORT = int(os.getenv('IMAP_PORT', '993'))
    IMAP_USERNAME = os.getenv('IMAP_USERNAME', '')  # 通常與SMTP相同
    IMAP_PASSWORD = os.getenv('IMAP_PASSWORD', '')  # 通常與SMTP相同

    # === Razer 相關設定 ===
    RAZER_LOGIN_URL = os.getenv('RAZER_LOGIN_URL', 'https://razer.com/login')
    RAZER_RECHARGE_URL = os.getenv('RAZER_RECHARGE_URL', 'https://razer.com/recharge')

    # === Google Authenticator OTP 設定 ===
    GOOGLE_AUTH_SECRET = os.getenv('GOOGLE_AUTH_SECRET', '')  # Base32 編碼的密鑰

    # === 自動化設定 ===
    SCREENSHOT_DIR = os.getenv('SCREENSHOT_DIR', './screenshots')
    CHROME_DRIVER_PATH = os.getenv('CHROME_DRIVER_PATH', './chromedriver')
    ZIP_OUTPUT_DIR = os.getenv('ZIP_OUTPUT_DIR', './zip_files')

    # === 系統設定 ===
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', '10485760'))  # 10MB
    ALLOWED_EXTENSIONS = os.getenv('ALLOWED_EXTENSIONS', 'png,jpg,jpeg,gif,zip').split(',')

    # === 日誌設定 ===
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', './logs/app.log')

    # === Redis 設定（可選，用於快取） ===
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    # === 安全設定 ===
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '3600'))  # 1小時
    MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', '5'))
    LOCKOUT_DURATION = int(os.getenv('LOCKOUT_DURATION', '1800'))  # 30分鐘

    # === API 設定 ===
    API_RATE_LIMIT = int(os.getenv('API_RATE_LIMIT', '100'))  # 每分鐘請求次數
    API_TIMEOUT = int(os.getenv('API_TIMEOUT', '30'))  # 超時時間（秒）

    # === 業務設定 ===
    MIN_TOP_UP_AMOUNT = float(os.getenv('MIN_TOP_UP_AMOUNT', '100.0'))
    MAX_TOP_UP_AMOUNT = float(os.getenv('MAX_TOP_UP_AMOUNT', '10000.0'))
    DEFAULT_CURRENCY = os.getenv('DEFAULT_CURRENCY', 'TWD')
    TOKEN_EXCHANGE_RATE = float(os.getenv('TOKEN_EXCHANGE_RATE', '1.0'))  # 1 NT$ = 1 Token

    # === 通知設定 ===
    ADMIN_EMAILS = os.getenv('ADMIN_EMAILS', '').split(',') if os.getenv('ADMIN_EMAILS') else []
    ENABLE_EMAIL_NOTIFICATIONS = os.getenv('ENABLE_EMAIL_NOTIFICATIONS', 'True').lower() == 'true'

    # === 自動化執行設定 ===
    AUTO_CLEANUP_DAYS = int(os.getenv('AUTO_CLEANUP_DAYS', '7'))
    SCREENSHOT_RETENTION_DAYS = int(os.getenv('SCREENSHOT_RETENTION_DAYS', '30'))
    MAX_CONCURRENT_AUTOMATIONS = int(os.getenv('MAX_CONCURRENT_AUTOMATIONS', '3'))

    @classmethod
    def validate_config(cls) -> bool:
        """
        驗證配置是否完整

        Returns:
            配置是否有效
        """
        required_vars = [
            'CHANNEL_ACCESS_TOKEN',
            'CHANNEL_SECRET',
            'SECRET_KEY'
        ]

        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)

        if missing_vars:
            print(f"缺少必要的環境變數: {', '.join(missing_vars)}")
            return False

        return True

    @classmethod
    def get_database_config(cls) -> dict:
        """
        取得資料庫配置

        Returns:
            資料庫配置字典
        """
        return {
            'url': cls.DATABASE_URL,
            'echo': cls.DEBUG,
            'pool_pre_ping': True,
            'pool_recycle': 3600
        }

    @classmethod
    def get_logging_config(cls) -> dict:
        """
        取得日誌配置

        Returns:
            日誌配置字典
        """
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'default': {
                    'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
                },
                'detailed': {
                    'format': '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'default',
                    'level': cls.LOG_LEVEL
                },
                'file': {
                    'class': 'logging.FileHandler',
                    'filename': cls.LOG_FILE,
                    'formatter': 'detailed',
                    'level': cls.LOG_LEVEL,
                    'encoding': 'utf-8'
                }
            },
            'root': {
                'level': cls.LOG_LEVEL,
                'handlers': ['console', 'file']
            }
        }

class DevelopmentConfig(Config):
    """開發環境配置"""
    DEBUG = True

class ProductionConfig(Config):
    """生產環境配置"""
    DEBUG = False

class TestingConfig(Config):
    """測試環境配置"""
    TESTING = True
    DATABASE_URL = 'sqlite:///:memory:'

# 根據環境選擇配置
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
