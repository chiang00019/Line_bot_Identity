# -*- coding: utf-8 -*-
"""
資料庫連線與會話管理
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import logging
from config.settings import Config

logger = logging.getLogger(__name__)

# 建立資料庫引擎
engine = create_engine(
    Config.DATABASE_URL,
    echo=Config.DEBUG,
    pool_pre_ping=True,
    pool_recycle=3600
)

# 建立 Session 工廠
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基礎模型類別
Base = declarative_base()

def get_db() -> Session:
    """
    取得資料庫會話 (用於 FastAPI 依賴注入)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_session():
    """
    取得資料庫會話 (用於一般業務邏輯)
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"資料庫操作失敗: {str(e)}")
        raise
    finally:
        db.close()

def init_database():
    """
    初始化資料庫 - 建立所有資料表
    """
    try:
        from app.models import Base
        Base.metadata.create_all(bind=engine)
        logger.info("資料庫初始化完成")
    except Exception as e:
        logger.error(f"資料庫初始化失敗: {str(e)}")
        raise

def drop_all_tables():
    """
    刪除所有資料表 (僅用於開發/測試)
    """
    try:
        from app.models import Base
        Base.metadata.drop_all(bind=engine)
        logger.warning("已刪除所有資料表")
    except Exception as e:
        logger.error(f"刪除資料表失敗: {str(e)}")
        raise
