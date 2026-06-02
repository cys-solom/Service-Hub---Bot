# -*- coding: utf-8 -*-
"""Referral commission service — auto-credit referrer when order is delivered."""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
from models.user import User
from models.referral import Referral
from models.wallet import Wallet, WalletTransaction
from models.system import AppSetting

logger = logging.getLogger(__name__)


async def _get_setting(session: AsyncSession, key: str, fallback: str = "") -> str:
    try:
        row = (await session.execute(
            select(AppSetting).where(AppSetting.key == key, AppSetting.is_deleted == False)
        )).scalar_one_or_none()
        if row and row.value:
            return row.value
    except Exception:
        pass
    return fallback


async def credit_referral_commission(session: AsyncSession, user_id, order_amount: float):
    """
    Check if the user who placed the order was referred.
    If yes, credit the referrer's wallet with the commission.
    
    Call this AFTER order.status = 'delivered' and session.commit().
    """
    try:
        # Check if system is enabled
        enabled = (await _get_setting(session, "referral_enabled", "true")) == "true"
        if not enabled:
            return

        auto_credit = (await _get_setting(session, "referral_auto_credit", "true")) == "true"
        if not auto_credit:
            return

        min_amount = float(await _get_setting(session, "referral_min_order_amount", "0"))
        if order_amount < min_amount:
            return

        # Find the referral record where this user is the referred person
        referral = (await session.execute(
            select(Referral).where(
                Referral.referred_id == user_id,
                Referral.is_deleted == False,
                Referral.status == "active",
            )
        )).scalar_one_or_none()

        if not referral:
            return

        # Calculate commission
        commission = round(order_amount * referral.commission_percent / 100, 2)
        if commission <= 0:
            return

        # Get referrer's wallet
        referrer_wallet = (await session.execute(
            select(Wallet).where(Wallet.user_id == referral.referrer_id)
        )).scalar_one_or_none()

        if not referrer_wallet:
            # Create wallet if missing
            referrer_wallet = Wallet(user_id=referral.referrer_id, balance=0, currency="USD")
            session.add(referrer_wallet)
            await session.flush()

        # Credit commission
        before = referrer_wallet.balance
        referrer_wallet.balance += commission
        referrer_wallet.total_deposited += commission

        # Log transaction
        session.add(WalletTransaction(
            wallet_id=referrer_wallet.id,
            type="referral_commission",
            amount=commission,
            balance_before=before,
            balance_after=referrer_wallet.balance,
            description=f"Referral commission ({referral.commission_percent}%) from order ${order_amount:.2f}",
        ))

        # Update referral stats
        referral.total_earned += commission
        referral.total_orders += 1

        await session.commit()

        logger.info(
            f"[Referral] Credited ${commission:.2f} to referrer "
            f"(user_id={referral.referrer_id}) from order ${order_amount:.2f}"
        )

    except Exception as e:
        logger.error(f"[Referral] Commission error: {e}", exc_info=True)
