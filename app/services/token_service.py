# -*- coding: utf-8 -*-
"""
Token 服務 - 處理群組共享Token餘額和交易記錄
"""

import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.database import get_db_session
from app.models import Group, User, GroupMember, TokenLog, TransactionType
from datetime import datetime

logger = logging.getLogger(__name__)

class TokenService:
    """Token 服務類別 - 支援群組共享Token管理"""

    def _perform_update_balance(self,
                               db: Session,
                               line_group_id: str,
                               amount: float,
                               transaction_type: str,
                               operator: str = "系統",
                               reference_id: Optional[str] = None,
                               description: Optional[str] = None,
                               user_id_for_log: Optional[int] = None):
        """
        執行實際的群組Token餘額更新和日誌記錄 (在提供的 db session 中操作)
        """
        group = db.query(Group).filter(Group.line_group_id == line_group_id).first()
        if not group:
            logger.warning(f"群組不存在: {line_group_id} (perform_update_balance)")
            return False

        if reference_id:
            existing_token_log = db.query(TokenLog).filter(TokenLog.reference_id == reference_id).first()
            if existing_token_log:
                logger.warning(f"重複的 TokenLog 參考ID: {reference_id}。可能是重複的交易或操作。")
                return False

        if amount < 0 and group.token_balance + amount < 0:
            logger.warning(f"群組餘額不足: {line_group_id}, 當前餘額: {group.token_balance}, 嘗試操作: {amount}")
            return False

        balance_before = group.token_balance
        group.token_balance += amount
        balance_after = group.token_balance

        actual_transaction_type = transaction_type
        if isinstance(transaction_type, str):
            try:
                actual_transaction_type = TransactionType[transaction_type.upper()]
            except KeyError:
                logger.warning(f"無效的 transaction_type 字串: {transaction_type}，將使用原始字串。")

        token_log_entry = TokenLog(
            group_id=group.id,
            user_id=user_id_for_log,
            transaction_type=actual_transaction_type.value if isinstance(actual_transaction_type, Enum) else actual_transaction_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_id=reference_id,
            description=description or f"Token {('增加' if amount > 0 else '減少')}: {abs(amount):.1f}",
            operator=operator
        )
        db.add(token_log_entry)
        logger.info(f"群組 {line_group_id} Token 更新預備: {amount:+.1f}, 新餘額: {balance_after:.1f} (等待 commit)")
        return True

    def update_group_balance(self,
                           line_group_id: str,
                           amount: float,
                           transaction_type: str,
                           operator: str = "系統",
                           reference_id: Optional[str] = None,
                           description: Optional[str] = None,
                           user_line_id_for_log: Optional[str] = None,
                           db_session: Optional[Session] = None) -> bool:
        """
        更新群組Token餘額。如果提供了 db_session，則在該 session 中操作。
        """
        user_id_for_log_db = None
        if user_line_id_for_log:
            def get_user_id(db_s: Session):
                user = db_s.query(User.id).filter(User.line_user_id == user_line_id_for_log).first()
                return user.id if user else None

            if db_session:
                user_id_for_log_db = get_user_id(db_session)
            else:
                with get_db_session() as temp_db:
                    user_id_for_log_db = get_user_id(temp_db)

        if db_session:
            return self._perform_update_balance(
                db_session, line_group_id, amount, transaction_type,
                operator, reference_id, description, user_id_for_log_db
            )
        else:
            try:
                with get_db_session() as db:
                    success = self._perform_update_balance(
                        db, line_group_id, amount, transaction_type,
                        operator, reference_id, description, user_id_for_log_db
                    )
                    if success:
                        db.commit()
                        logger.info(f"群組 {line_group_id} Token 更新成功 (獨立事務): {amount:+.1f}")
                        return True
                    else:
                        db.rollback()
                        logger.warning(f"群組 {line_group_id} Token 更新失敗 (獨立事務)")
                        return False
            except Exception as e:
                logger.error(f"更新群組Token時發生未預期錯誤 (獨立事務): {e}")
                return False

    def add_tokens_from_deposit(self,
                              line_group_id: str,
                              amount: float,
                              transfer_id: str,
                              description: Optional[str] = None,
                              db_session: Optional[Session] = None) -> bool:
        """
        從轉帳充值增加Token

        Args:
            line_group_id: Line群組ID
            amount: 充值金額
            transfer_id: 轉帳ID
            description: 描述

        Returns:
            是否成功
        """
        logger.info(f"Attempting to add {amount} tokens for group {line_group_id} from deposit (transfer_id: {transfer_id})")
        return self.update_group_balance(
            line_group_id=line_group_id,
            amount=amount,
            transaction_type=TransactionType.DEPOSIT,
            operator="Email自動對帳",
            reference_id=f"deposit_transfer_{transfer_id}",
            description=description or f"Email自動對帳 NT${amount:.0f}",
            db_session=db_session
        )

    def deduct_tokens_for_recharge(self,
                                 line_group_id: str,
                                 amount: float,
                                 razer_account: str,
                                 user_id: str = None) -> bool:
        """
        為Razer儲值扣除Token

        Args:
            line_group_id: Line群組ID
            amount: 儲值金額
            razer_account: Razer帳號
            user_id: 操作用戶ID

        Returns:
            是否成功
        """
        return self.update_group_balance(
            line_group_id=line_group_id,
            amount=-amount,
            transaction_type=TransactionType.WITHDRAW,
            operator=f"用戶儲值",
            reference_id=f"recharge_{line_group_id}_{int(datetime.now().timestamp())}",
            description=f"Razer儲值 {razer_account} NT${amount:.0f}"
        )

    def manual_adjust_tokens(self,
                           line_group_id: str,
                           amount: float,
                           operator: str,
                           description: str) -> bool:
        """
        管理員手動調整Token

        Args:
            line_group_id: Line群組ID
            amount: 調整金額（正負數）
            operator: 操作者
            description: 調整原因

        Returns:
            是否成功
        """
        transaction_type = TransactionType.MANUAL_ADD if amount > 0 else TransactionType.MANUAL_SUB

        return self.update_group_balance(
            line_group_id=line_group_id,
            amount=amount,
            transaction_type=transaction_type,
            operator=operator,
            reference_id=f"manual_{line_group_id}_{int(datetime.now().timestamp())}",
            description=description
        )

    def get_group_transaction_history(self, line_group_id: str, limit: int = 20) -> List[Dict]:
        """
        取得群組交易歷史

        Args:
            line_group_id: Line群組ID
            limit: 返回記錄數量限制

        Returns:
            交易歷史列表
        """
        try:
            with get_db_session() as db:
                group = db.query(Group).filter_by(line_group_id=line_group_id).first()
                if not group:
                    logger.warning(f"群組不存在: {line_group_id}")
                    return []

                # 查詢交易歷史
                token_logs = db.query(TokenLog)\
                    .filter_by(group_id=group.id)\
                    .order_by(TokenLog.created_at.desc())\
                    .limit(limit)\
                    .all()

                result = []
                for log in token_logs:
                    result.append({
                        'id': log.id,
                        'type': log.transaction_type,
                        'amount': log.amount,
                        'balance_before': log.balance_before,
                        'balance_after': log.balance_after,
                        'description': log.description,
                        'operator': log.operator,
                        'created_at': log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'reference_id': log.reference_id
                    })

                return result

        except Exception as e:
            logger.error(f"查詢群組交易歷史時發生錯誤: {str(e)}")
            return []

    def is_group_exists(self, line_group_id: str) -> bool:
        """
        檢查群組是否存在

        Args:
            line_group_id: Line群組ID

        Returns:
            群組是否存在
        """
        try:
            with get_db_session() as db:
                group = db.query(Group).filter_by(line_group_id=line_group_id).first()
                return group is not None
        except Exception as e:
            logger.error(f"檢查群組存在性時發生錯誤: {str(e)}")
            return False

    def is_user_admin(self, line_user_id: str, line_group_id: str) -> bool:
        """
        檢查用戶是否為群組管理員

        Args:
            line_user_id: Line用戶ID
            line_group_id: Line群組ID

        Returns:
            是否為管理員
        """
        try:
            with get_db_session() as db:
                group = db.query(Group).filter_by(line_group_id=line_group_id).first()
                if not group:
                    return False

                user = db.query(User).filter_by(line_user_id=line_user_id).first()
                if not user:
                    return False

                member = db.query(GroupMember).filter_by(
                    group_id=group.id, user_id=user.id, is_admin=True
                ).first()

                return member is not None
        except Exception as e:
            logger.error(f"檢查管理員權限時發生錯誤: {str(e)}")
            return False

    def get_group_info(self, line_group_id: str) -> Optional[Dict]:
        """
        取得群組完整資訊

        Args:
            line_group_id: Line群組ID

        Returns:
            群組資訊字典或None
        """
        try:
            with get_db_session() as db:
                group = db.query(Group).filter_by(line_group_id=line_group_id).first()
                if not group:
                    return None

                # 查詢群組成員
                members = db.query(GroupMember, User)\
                    .join(User)\
                    .filter(GroupMember.group_id == group.id)\
                    .all()

                member_list = []
                admin_count = 0
                for member, user in members:
                    member_info = {
                        'user_id': user.line_user_id,
                        'display_name': user.display_name,
                        'is_admin': member.is_admin,
                        'joined_at': member.joined_at.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    member_list.append(member_info)
                    if member.is_admin:
                        admin_count += 1

                return {
                    'group_id': group.line_group_id,
                    'group_name': group.group_name,
                    'token_balance': group.token_balance,
                    'is_active': group.is_active,
                    'created_at': group.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'member_count': len(member_list),
                    'admin_count': admin_count,
                    'members': member_list
                }

        except Exception as e:
            logger.error(f"取得群組資訊時發生錯誤: {str(e)}")
            return None

    def get_group_balance(self, line_group_id: str) -> Optional[float]:
        """
        取得群組Token餘額

        Args:
            line_group_id: Line群組ID

        Returns:
            群組Token餘額，如果群組不存在則返回None
        """
        try:
            with get_db_session() as db:
                group = db.query(Group).filter_by(line_group_id=line_group_id).first()
                if not group:
                    logger.warning(f"群組不存在: {line_group_id}")
                    return None
                return group.token_balance
        except Exception as e:
            logger.error(f"查詢群組餘額時發生錯誤: {str(e)}")
            return None
