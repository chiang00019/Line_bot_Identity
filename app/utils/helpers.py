# -*- coding: utf-8 -*-
"""
工具函式 - 各種輔助函式
"""

import hashlib
import secrets
import string
import re
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from cryptography.fernet import Fernet
from config.settings import Config

logger = logging.getLogger(__name__)

def generate_random_string(length: int = 16, include_special: bool = False) -> str:
    """
    生成隨機字符串

    Args:
        length: 字符串長度
        include_special: 是否包含特殊字符

    Returns:
        隨機字符串
    """
    characters = string.ascii_letters + string.digits
    if include_special:
        characters += "!@#$%^&*"

    return ''.join(secrets.choice(characters) for _ in range(length))

def generate_order_id(prefix: str = "ORDER") -> str:
    """
    生成訂單ID

    Args:
        prefix: 訂單前綴

    Returns:
        唯一訂單ID
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = generate_random_string(6, include_special=False)
    return f"{prefix}_{timestamp}_{random_suffix}"

def encrypt_data(data: str, key: Optional[str] = None) -> str:
    """
    加密數據

    Args:
        data: 要加密的數據
        key: 加密密鑰，如果不提供則使用配置中的密鑰

    Returns:
        加密後的數據
    """
    try:
        if not key:
            key = Config.ENCRYPTION_KEY

        f = Fernet(key.encode())
        encrypted_data = f.encrypt(data.encode())
        return encrypted_data.decode()

    except Exception as e:
        logger.error(f"數據加密失敗: {str(e)}")
        return ""

def decrypt_data(encrypted_data: str, key: Optional[str] = None) -> str:
    """
    解密數據

    Args:
        encrypted_data: 加密的數據
        key: 解密密鑰，如果不提供則使用配置中的密鑰

    Returns:
        解密後的數據
    """
    try:
        if not key:
            key = Config.ENCRYPTION_KEY

        f = Fernet(key.encode())
        decrypted_data = f.decrypt(encrypted_data.encode())
        return decrypted_data.decode()

    except Exception as e:
        logger.error(f"數據解密失敗: {str(e)}")
        return ""

def hash_password(password: str, salt: Optional[str] = None) -> Dict[str, str]:
    """
    哈希密碼

    Args:
        password: 原始密碼
        salt: 鹽值，如果不提供則自動生成

    Returns:
        包含哈希值和鹽值的字典
    """
    if not salt:
        salt = secrets.token_hex(16)

    # 使用PBKDF2算法哈希密碼
    password_hash = hashlib.pbkdf2_hmac('sha256',
                                       password.encode('utf-8'),
                                       salt.encode('utf-8'),
                                       100000)

    return {
        'hash': password_hash.hex(),
        'salt': salt
    }

def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """
    驗證密碼

    Args:
        password: 要驗證的密碼
        stored_hash: 存儲的哈希值
        salt: 鹽值

    Returns:
        密碼是否正確
    """
    password_hash = hashlib.pbkdf2_hmac('sha256',
                                       password.encode('utf-8'),
                                       salt.encode('utf-8'),
                                       100000)

    return password_hash.hex() == stored_hash

def validate_email(email: str) -> bool:
    """
    驗證電子郵件格式

    Args:
        email: 電子郵件地址

    Returns:
        是否為有效的郵件格式
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone: str) -> bool:
    """
    驗證電話號碼格式（台灣）

    Args:
        phone: 電話號碼

    Returns:
        是否為有效的電話號碼格式
    """
    # 支援台灣手機號碼格式
    patterns = [
        r'^09\d{8}$',  # 09xxxxxxxx
        r'^\+8869\d{8}$',  # +88609xxxxxxxx
        r'^886-9\d{8}$',  # 886-9xxxxxxxx
    ]

    for pattern in patterns:
        if re.match(pattern, phone):
            return True

    return False

def format_currency(amount: float, currency: str = 'TWD') -> str:
    """
    格式化貨幣顯示

    Args:
        amount: 金額
        currency: 貨幣類型

    Returns:
        格式化後的貨幣字符串
    """
    currency_symbols = {
        'TWD': 'NT$',
        'USD': '$',
        'JPY': '¥',
        'EUR': '€',
        'GBP': '£'
    }

    symbol = currency_symbols.get(currency, currency)

    if currency in ['JPY', 'KRW']:
        return f"{symbol}{int(amount):,}"
    else:
        return f"{symbol}{amount:,.2f}"

def calculate_time_difference(start_time: datetime, end_time: datetime) -> str:
    """
    計算時間差並格式化顯示

    Args:
        start_time: 開始時間
        end_time: 結束時間

    Returns:
        格式化的時間差字符串
    """
    diff = end_time - start_time

    days = diff.days
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        return f"{days}天 {hours}小時 {minutes}分鐘"
    elif hours > 0:
        return f"{hours}小時 {minutes}分鐘"
    elif minutes > 0:
        return f"{minutes}分鐘 {seconds}秒"
    else:
        return f"{seconds}秒"

def sanitize_filename(filename: str) -> str:
    """
    清理檔案名稱，移除不安全字符

    Args:
        filename: 原始檔案名稱

    Returns:
        清理後的檔案名稱
    """
    # 移除或替換不安全字符
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')

    # 移除開頭和結尾的空格和點
    filename = filename.strip(' .')

    # 限制長度
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext

    return filename

def parse_json_safely(json_string: str) -> Optional[Dict[str, Any]]:
    """
    安全地解析JSON字符串

    Args:
        json_string: JSON字符串

    Returns:
        解析後的字典，失敗則返回None
    """
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"JSON解析失敗: {str(e)}")
        return None

def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    將列表分割成指定大小的塊

    Args:
        lst: 要分割的列表
        chunk_size: 每塊的大小

    Returns:
        分割後的列表列表
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def is_business_hour(hour_range: tuple = (9, 18)) -> bool:
    """
    檢查當前是否為營業時間

    Args:
        hour_range: 營業時間範圍 (開始小時, 結束小時)

    Returns:
        是否為營業時間
    """
    current_hour = datetime.now().hour
    start_hour, end_hour = hour_range

    return start_hour <= current_hour < end_hour

def mask_sensitive_data(data: str, mask_char: str = '*', visible_chars: int = 4) -> str:
    """
    遮蔽敏感資料

    Args:
        data: 原始資料
        mask_char: 遮蔽字符
        visible_chars: 顯示的字符數（開頭和結尾各顯示一半）

    Returns:
        遮蔽後的資料
    """
    if len(data) <= visible_chars:
        return mask_char * len(data)

    visible_start = visible_chars // 2
    visible_end = visible_chars - visible_start

    masked_length = len(data) - visible_chars
    masked_part = mask_char * masked_length

    return data[:visible_start] + masked_part + data[-visible_end:] if visible_end > 0 else data[:visible_start] + masked_part
