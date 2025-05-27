# -*- coding: utf-8 -*-
"""
資料庫模型定義 - 支援群組共享 Token 與自動化管理
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum

Base = declarative_base()

class TransactionType(str, Enum):
    """交易類型枚舉"""
    DEPOSIT = "deposit"          # 充值 Token
    WITHDRAW = "withdraw"        # 消費 Token (儲值)
    MANUAL_ADD = "manual_add"    # 管理員手動添加
    MANUAL_SUB = "manual_sub"    # 管理員手動扣除

class TransactionStatus(str, Enum):
    """交易狀態枚舉"""
    PENDING = "pending"          # 等待中
    SUCCESS = "success"          # 成功
    FAILED = "failed"           # 失敗
    CANCELLED = "cancelled"      # 已取消

class Group(Base):
    """Line 群組資料表"""
    __tablename__ = 'groups'

    id = Column(Integer, primary_key=True, autoincrement=True)
    line_group_id = Column(String(255), unique=True, nullable=False, comment='Line群組ID')
    group_name = Column(String(255), comment='群組名稱')
    token_balance = Column(Float, default=0.0, comment='群組共享Token餘額')
    is_active = Column(Boolean, default=True, comment='群組是否啟用')
    created_at = Column(DateTime, default=func.now(), comment='群組建立時間')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='最後更新時間')

    # 關聯關係
    members = relationship("GroupMember", back_populates="group")
    token_logs = relationship("TokenLog", back_populates="group")
    razer_logs = relationship("RazerLog", back_populates="group")
    email_logs = relationship("EmailLog", back_populates="group")

    def __repr__(self):
        return f"<Group(line_group_id='{self.line_group_id}', token_balance={self.token_balance})>"

class User(Base):
    """用戶資料表"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    line_user_id = Column(String(255), unique=True, nullable=False, comment='Line用戶ID')
    display_name = Column(String(255), comment='用戶顯示名稱')
    created_at = Column(DateTime, default=func.now(), comment='用戶建立時間')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='最後更新時間')

    # 關聯關係
    group_memberships = relationship("GroupMember", back_populates="user")

    def __repr__(self):
        return f"<User(line_user_id='{self.line_user_id}', display_name='{self.display_name}')>"

class GroupMember(Base):
    """群組成員關係表"""
    __tablename__ = 'group_members'

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=False, comment='群組ID')
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment='用戶ID')
    is_admin = Column(Boolean, default=False, comment='是否為管理員')
    joined_at = Column(DateTime, default=func.now(), comment='加入時間')

    # 關聯關係
    group = relationship("Group", back_populates="members")
    user = relationship("User", back_populates="group_memberships")

    # 複合唯一索引，確保同一用戶在同一群組只能有一筆記錄
    __table_args__ = (Index('idx_group_user', 'group_id', 'user_id', unique=True),)

    def __repr__(self):
        return f"<GroupMember(group_id={self.group_id}, user_id={self.user_id}, is_admin={self.is_admin})>"

class TokenLog(Base):
    """Token 交易記錄表"""
    __tablename__ = 'token_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=False, comment='群組ID')
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, comment='操作用戶ID')
    transaction_type = Column(String(20), nullable=False, comment='交易類型')
    amount = Column(Float, nullable=False, comment='金額')
    balance_before = Column(Float, nullable=False, comment='操作前餘額')
    balance_after = Column(Float, nullable=False, comment='操作後餘額')
    reference_id = Column(String(255), comment='參考ID(防重複用)')
    description = Column(Text, comment='交易描述')
    operator = Column(String(255), comment='操作者 (系統/用戶)')
    created_at = Column(DateTime, default=func.now(), comment='交易時間')

    # 關聯關係
    group = relationship("Group", back_populates="token_logs")

    def __repr__(self):
        return f"<TokenLog(group_id={self.group_id}, type='{self.transaction_type}', amount={self.amount})>"

class EmailLog(Base):
    """Email 對帳記錄表"""
    __tablename__ = 'email_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=False, comment='群組ID')
    email_subject = Column(String(500), comment='Email主旨')
    sender = Column(String(255), comment='寄件者')
    transfer_amount = Column(Float, comment='轉帳金額')
    transfer_id = Column(String(255), unique=True, comment='轉帳唯一識別ID')
    transfer_time = Column(DateTime, comment='轉帳時間')
    processing_status = Column(String(20), default='pending', comment='處理狀態')
    tokens_added = Column(Float, default=0.0, comment='已添加的Token數量')
    error_message = Column(Text, comment='錯誤訊息')
    processed_at = Column(DateTime, comment='處理時間')
    created_at = Column(DateTime, default=func.now(), comment='Email接收時間')

    # 關聯關係
    group = relationship("Group", back_populates="email_logs")

    def __repr__(self):
        return f"<EmailLog(transfer_id='{self.transfer_id}', amount={self.transfer_amount}, status='{self.processing_status}')>"

class RazerLog(Base):
    """Razer 儲值記錄表"""
    __tablename__ = 'razer_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=False, comment='群組ID')
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment='操作用戶ID')
    razer_account = Column(String(255), nullable=False, comment='Razer帳號')
    amount = Column(Float, nullable=False, comment='儲值金額')
    tokens_used = Column(Float, nullable=False, comment='消費的Token數量')
    status = Column(String(20), default='pending', comment='儲值狀態')
    razer_transaction_id = Column(String(255), comment='Razer交易ID')
    screenshot_count = Column(Integer, default=0, comment='截圖數量')
    screenshot_paths = Column(Text, comment='截圖路徑列表(JSON)')
    zip_file_path = Column(String(500), comment='ZIP檔案路徑')
    execution_time = Column(Float, comment='執行時間(秒)')
    error_message = Column(Text, comment='錯誤訊息')
    retry_count = Column(Integer, default=0, comment='重試次數')
    created_at = Column(DateTime, default=func.now(), comment='建立時間')
    completed_at = Column(DateTime, comment='完成時間')

    # 關聯關係
    group = relationship("Group", back_populates="razer_logs")

    def __repr__(self):
        return f"<RazerLog(group_id={self.group_id}, account='{self.razer_account}', amount={self.amount}, status='{self.status}')>"

class SystemConfig(Base):
    """系統設定表"""
    __tablename__ = 'system_config'

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False, comment='設定鍵值')
    config_value = Column(Text, comment='設定值')
    description = Column(Text, comment='設定描述')
    is_active = Column(Boolean, default=True, comment='是否啟用')
    created_at = Column(DateTime, default=func.now(), comment='建立時間')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新時間')

    def __repr__(self):
        return f"<SystemConfig(key='{self.config_key}', value='{self.config_value}')>"
