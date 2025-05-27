# -*- coding: utf-8 -*-
"""
Token 服務 - 處理群組共享Token餘額和交易記錄
"""

import logging
from typing import Optional, Dict, Any, List
from app.database import get_db_session
from app.models import Group, User, GroupMember, TokenLog, TransactionType
from datetime import datetime

logger = logging.getLogger(__name__)

class TokenService:
    """Token 服務類別 - 支援群組共享Token管理"""

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

    def update_group_balance(self,
                           line_group_id: str,
                           amount: float,
                           transaction_type: str,
                           operator: str = "系統",
                           reference_id: str = None,
                           description: str = None) -> bool:
        """
        更新群組Token餘額

        Args:
            line_group_id: Line群組ID
            amount: 變更金額（正數為增加，負數為減少）
            transaction_type: 交易類型
            operator: 操作者
            reference_id: 參考ID（防重複）
            description: 交易描述

        Returns:
            更新是否成功
        """
        try:
            with get_db_session() as db:
                group = db.query(Group).filter_by(line_group_id=line_group_id).first()
                if not group:
                    logger.warning(f"群組不存在: {line_group_id}")
                    return False

                # 檢查參考ID是否已存在（防重複）
                if reference_id:
                    existing_log = db.query(TokenLog).filter_by(reference_id=reference_id).first()
                    if existing_log:
                        logger.warning(f"重複的交易參考ID: {reference_id}")
                        return False

                # 檢查餘額是否足夠（對於扣除操作）
                if amount < 0 and group.token_balance + amount < 0:
                    logger.warning(f"群組餘額不足: {line_group_id}, 當前餘額: {group.token_balance}, 嘗試扣除: {abs(amount)}")
                    return False

                # 記錄變更前餘額
                balance_before = group.token_balance

                # 更新餘額
                group.token_balance += amount
                balance_after = group.token_balance

                # 建立交易記錄
                token_log = TokenLog(
                    group_id=group.id,
                    transaction_type=transaction_type,
                    amount=amount,
                    balance_before=balance_before,
                    balance_after=balance_after,
                    reference_id=reference_id,
                    description=description or f"Token{('增加' if amount > 0 else '減少')}: {abs(amount)}",
                    operator=operator
                )
                db.add(token_log)

                db.commit()
                logger.info(f"群組 {line_group_id} Token更新成功: {amount:+.1f}, 新餘額: {balance_after:.1f}")
                return True

        except Exception as e:
            logger.error(f"更新群組Token時發生錯誤: {str(e)}")
            return False

    def add_tokens_from_deposit(self,
                              line_group_id: str,
                              amount: float,
                              transfer_id: str,
                              description: str = None) -> bool:
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
        return self.update_group_balance(
            line_group_id=line_group_id,
            amount=amount,
            transaction_type=TransactionType.DEPOSIT,
            operator="Email自動對帳",
            reference_id=f"transfer_{transfer_id}",
            description=description or f"Email自動對帳充值 NT${amount:.0f}"
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
