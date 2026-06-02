"""Users API — with admin deposit, Telegram notification, referral data, and user details"""
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_admin
from core.telegram import send_telegram
from core.cms import render as cms_render
from models.user import User
from models.wallet import Wallet, WalletTransaction
from models.referral import Referral
from models.order import Order, OrderItem
from models.catalog import Product

router = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger(__name__)


def _display_name(u):
    if not u:
        return "N/A"
    parts = [u.first_name or "", u.last_name or ""]
    name = " ".join(p for p in parts if p).strip()
    return name or u.username or "N/A"


@router.get("")
async def list_users(
    search: str = "", page: int = 1, limit: int = 20,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    query = select(User).where(User.is_deleted == False)
    count_q = select(func.count(User.id)).where(User.is_deleted == False)
    if search:
        if search.isdigit():
            query = query.where(User.telegram_id == int(search))
            count_q = count_q.where(User.telegram_id == int(search))
        else:
            query = query.where(User.username.ilike(f"%{search}%"))
            count_q = count_q.where(User.username.ilike(f"%{search}%"))

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(query.order_by(desc(User.created_at)).offset((page-1)*limit).limit(limit))
    users = []
    for u in result.scalars().all():
        wallet = (await db.execute(select(Wallet).where(Wallet.user_id == u.id))).scalar_one_or_none()

        # Referral data
        ref_count = (await db.execute(
            select(func.count(Referral.id))
            .where(Referral.referrer_id == u.id, Referral.is_deleted == False)
        )).scalar() or 0

        ref_earnings = (await db.execute(
            select(func.coalesce(func.sum(Referral.total_earned), 0))
            .where(Referral.referrer_id == u.id, Referral.is_deleted == False)
        )).scalar() or 0

        # Who referred this user
        referred_by = None
        if u.referred_by_id:
            try:
                referrer = (await db.execute(
                    select(User).where(User.telegram_id == int(u.referred_by_id))
                )).scalar_one_or_none()
                if referrer:
                    referred_by = referrer.username or _display_name(referrer)
            except (ValueError, TypeError):
                pass

        users.append({
            "id": str(u.id), "telegram_id": u.telegram_id,
            "username": u.username or "N/A",
            "display_name": _display_name(u),
            "first_name": u.first_name, "last_name": u.last_name,
            "language": u.language_code,
            "balance": round(wallet.balance, 2) if wallet else 0,
            "total_spent": round(u.total_spent, 2),
            "total_orders": u.total_orders,
            "is_banned": u.is_banned,
            "joined": u.created_at.isoformat(),
            "referral_count": ref_count,
            "referral_earnings": round(float(ref_earnings), 2),
            "referred_by": referred_by,
        })
    return {"users": users, "total": total, "page": page, "pages": max(1, (total+limit-1)//limit)}


# ─── User Details ─────────────────────────────────────

@router.get("/{user_id}/details")
async def user_details(
    user_id: str,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    user = (await db.execute(select(User).where(User.id == uuid.UUID(user_id)))).scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    wallet = (await db.execute(select(Wallet).where(Wallet.user_id == user.id))).scalar_one_or_none()

    # ─ Orders ─
    orders_result = await db.execute(
        select(Order).where(Order.user_id == user.id, Order.is_deleted == False)
        .order_by(desc(Order.created_at)).limit(50)
    )
    orders = []
    for o in orders_result.scalars().all():
        # Get product name from order items
        oi = (await db.execute(
            select(OrderItem).where(OrderItem.order_id == o.id)
        )).scalars().first()
        product_name = "Unknown"
        if oi:
            prod = (await db.execute(select(Product).where(Product.id == oi.product_id))).scalar_one_or_none()
            if prod:
                product_name = prod.name

        orders.append({
            "id": str(o.id),
            "order_number": o.order_number,
            "product_name": product_name,
            "amount": round(o.final_amount, 2),
            "status": o.status,
            "created_at": o.created_at.isoformat(),
        })

    # ─ Referrals (people this user invited) ─
    refs_result = await db.execute(
        select(Referral).where(Referral.referrer_id == user.id, Referral.is_deleted == False)
        .order_by(desc(Referral.created_at))
    )
    referrals = []
    for r in refs_result.scalars().all():
        referred = (await db.execute(select(User).where(User.id == r.referred_id))).scalar_one_or_none()
        referrals.append({
            "id": str(r.id),
            "referred_name": _display_name(referred),
            "referred_username": referred.username if referred else "N/A",
            "commission_percent": r.commission_percent,
            "total_earned": round(r.total_earned, 2),
            "total_orders": r.total_orders,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
        })

    # ─ Wallet Transactions ─
    transactions = []
    if wallet:
        tx_result = await db.execute(
            select(WalletTransaction).where(WalletTransaction.wallet_id == wallet.id)
            .order_by(desc(WalletTransaction.created_at)).limit(50)
        )
        for tx in tx_result.scalars().all():
            transactions.append({
                "id": str(tx.id),
                "type": tx.type,
                "amount": round(tx.amount, 2),
                "balance_after": round(tx.balance_after, 2),
                "description": tx.description,
                "created_at": tx.created_at.isoformat(),
            })

    # ─ Stats ─
    order_count = (await db.execute(
        select(func.count(Order.id)).where(Order.user_id == user.id, Order.is_deleted == False)
    )).scalar() or 0

    delivered_count = (await db.execute(
        select(func.count(Order.id)).where(
            Order.user_id == user.id, Order.status == "delivered", Order.is_deleted == False
        )
    )).scalar() or 0

    ref_count = (await db.execute(
        select(func.count(Referral.id)).where(Referral.referrer_id == user.id, Referral.is_deleted == False)
    )).scalar() or 0

    ref_earnings = (await db.execute(
        select(func.coalesce(func.sum(Referral.total_earned), 0))
        .where(Referral.referrer_id == user.id, Referral.is_deleted == False)
    )).scalar() or 0

    # Referred by
    referred_by_info = None
    if user.referred_by_id:
        try:
            referrer = (await db.execute(
                select(User).where(User.telegram_id == int(user.referred_by_id))
            )).scalar_one_or_none()
            if referrer:
                referred_by_info = {
                    "name": _display_name(referrer),
                    "username": referrer.username,
                    "telegram_id": referrer.telegram_id,
                }
        except (ValueError, TypeError):
            pass

    return {
        "user": {
            "id": str(user.id),
            "telegram_id": user.telegram_id,
            "username": user.username,
            "display_name": _display_name(user),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "language": user.language_code,
            "is_banned": user.is_banned,
            "is_premium": user.is_premium,
            "balance": round(wallet.balance, 2) if wallet else 0,
            "total_deposited": round(wallet.total_deposited, 2) if wallet else 0,
            "joined": user.created_at.isoformat(),
            "notes": user.notes,
        },
        "stats": {
            "total_orders": order_count,
            "delivered_orders": delivered_count,
            "total_spent": round(user.total_spent, 2),
            "referral_count": ref_count,
            "referral_earnings": round(float(ref_earnings), 2),
        },
        "referred_by": referred_by_info,
        "orders": orders,
        "referrals": referrals,
        "transactions": transactions,
    }


# ─── Ban / Balance ────────────────────────────────────

class UserBanAction(BaseModel):
    is_banned: bool

@router.put("/{user_id}/ban")
async def toggle_ban(
    user_id: str, data: UserBanAction,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    user = (await db.execute(select(User).where(User.id == uuid.UUID(user_id)))).scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    user.is_banned = data.is_banned
    await db.commit()
    return {"success": True}


class BalanceUpdate(BaseModel):
    amount: float
    operation: str  # add, deduct
    note: str = ""

@router.put("/{user_id}/balance")
async def update_balance(
    user_id: str, data: BalanceUpdate,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    user = (await db.execute(select(User).where(User.id == uuid.UUID(user_id)))).scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    wallet = (await db.execute(select(Wallet).where(Wallet.user_id == user.id))).scalar_one_or_none()
    if not wallet:
        wallet = Wallet(user_id=user.id, balance=0)
        db.add(wallet)
        await db.flush()

    before = wallet.balance

    if data.operation == "add":
        wallet.balance += data.amount
        wallet.total_deposited += data.amount
        tx_type = "admin_add"
        desc_text = data.note or f"Admin deposit +${data.amount:.2f}"
    else:
        wallet.balance = max(0, wallet.balance - data.amount)
        tx_type = "admin_deduct"
        desc_text = data.note or f"Admin deduction -${data.amount:.2f}"

    # Record transaction
    db.add(WalletTransaction(
        wallet_id=wallet.id, type=tx_type, amount=data.amount if data.operation == "add" else -data.amount,
        balance_before=before, balance_after=wallet.balance,
        description=desc_text,
    ))

    await db.commit()

    # Send Telegram notification using CMS templates
    if user.telegram_id:
        if data.operation == "add":
            msg = await cms_render(db, "notify_admin_deposit", "en",
                                   amount=f"{data.amount:.2f}",
                                   balance=f"{wallet.balance:.2f}",
                                   note=data.note or "Admin deposit")
        else:
            msg = await cms_render(db, "notify_balance_deducted", "en",
                                   amount=f"{data.amount:.2f}",
                                   balance=f"{wallet.balance:.2f}",
                                   note=data.note or "Admin deduction")

        if msg:
            await send_telegram(user.telegram_id, msg)
        logger.info(f"[Wallet] Notified {user.telegram_id}: {data.operation} ${data.amount}")

    return {"success": True, "balance": round(wallet.balance, 2)}
