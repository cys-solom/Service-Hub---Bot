"""Payments API — methods CRUD + deposit requests approval"""
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.config import settings
from core.security import get_current_admin
from core.telegram import send_telegram
from core.cms import render as cms_render
from models.payment import Payment, PaymentMethod
from models.user import User
from models.wallet import Wallet, WalletTransaction

router = APIRouter(prefix="/payments", tags=["payments"])
logger = logging.getLogger(__name__)


class PaymentMethodIn(BaseModel):
    name: str
    code: str
    type: str
    is_enabled: bool = True
    wallet_address: Optional[str] = None
    config: Optional[dict] = None
    icon: Optional[str] = None
    sort_order: int = 0
    min_amount: float = 0
    max_amount: float = 99999
    fee_percent: float = 0
    fee_fixed: float = 0
    instructions: Optional[str] = None
    instructions_i18n: Optional[dict] = None


@router.get("/methods")
async def list_payment_methods(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PaymentMethod).where(PaymentMethod.is_deleted == False).order_by(PaymentMethod.sort_order)
    )
    return {"methods": [{
        "id": str(m.id), "name": m.name, "code": m.code, "type": m.type,
        "is_enabled": m.is_enabled, "wallet_address": m.wallet_address,
        "config": m.config, "icon": m.icon, "sort_order": m.sort_order,
        "min_amount": m.min_amount, "max_amount": m.max_amount,
        "fee_percent": m.fee_percent, "fee_fixed": m.fee_fixed,
        "instructions": m.instructions, "instructions_i18n": m.instructions_i18n,
    } for m in result.scalars().all()]}


@router.post("/methods")
async def create_payment_method(
    data: PaymentMethodIn, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    method = PaymentMethod(**data.model_dump())
    db.add(method)
    await db.commit()
    return {"success": True, "id": str(method.id)}


@router.put("/methods/{method_id}")
async def update_payment_method(
    method_id: str, data: PaymentMethodIn,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    method = (await db.execute(
        select(PaymentMethod).where(PaymentMethod.id == uuid.UUID(method_id))
    )).scalar_one_or_none()
    if not method:
        raise HTTPException(404, "Payment method not found")
    for k, v in data.model_dump().items():
        setattr(method, k, v)
    await db.commit()
    return {"success": True}


# ═══════════════════════════════════════════
# DEPOSIT REQUESTS
# ═══════════════════════════════════════════

@router.get("")
async def list_payments(
    status: str = "", type: str = "", page: int = 1, limit: int = 20,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    query = select(Payment, User).join(User, Payment.user_id == User.id).where(Payment.is_deleted == False)
    count_q = select(func.count(Payment.id)).where(Payment.is_deleted == False)

    if status:
        query = query.where(Payment.status == status)
        count_q = count_q.where(Payment.status == status)

    # Filter deposits (no order_id) vs order payments
    if type == "deposit":
        query = query.where(Payment.order_id == None)
        count_q = count_q.where(Payment.order_id == None)
    elif type == "order":
        query = query.where(Payment.order_id != None)
        count_q = count_q.where(Payment.order_id != None)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(query.order_by(desc(Payment.created_at)).offset((page-1)*limit).limit(limit))

    return {
        "payments": [{
            "id": str(p.id),
            "order_id": str(p.order_id) if p.order_id else None,
            "user_id": str(p.user_id),
            "username": u.username or f"ID:{u.telegram_id}",
            "display_name": " ".join(filter(None, [u.first_name, u.last_name])) or u.username or f"ID:{u.telegram_id}",
            "telegram_id": u.telegram_id,
            "method_code": p.method_code,
            "amount": p.amount, "currency": p.currency, "status": p.status,
            "tx_hash": p.tx_hash, "tx_note": p.tx_note,
            "verification_type": p.verification_type,
            "is_deposit": p.order_id is None,
            "created_at": p.created_at.isoformat(),
        } for p, u in result.all()],
        "total": total, "page": page,
        "pages": max(1, (total + limit - 1) // limit),
    }


class BulkDeleteIn(BaseModel):
    ids: list[str]


@router.delete("/bulk")
async def bulk_delete_payments(
    data: BulkDeleteIn,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    """Delete multiple payments at once."""
    count = 0
    for pid in data.ids:
        p = (await db.execute(select(Payment).where(Payment.id == uuid.UUID(pid)))).scalar_one_or_none()
        if p:
            p.is_deleted = True
            count += 1
    await db.commit()
    return {"success": True, "deleted": count}


@router.post("/{payment_id}/approve")
async def approve_deposit(
    payment_id: str,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    """Approve a deposit request: add balance to user + notify via Telegram."""
    payment = (await db.execute(
        select(Payment).where(Payment.id == uuid.UUID(payment_id))
    )).scalar_one_or_none()
    if not payment:
        raise HTTPException(404, "Payment not found")
    if payment.status == "confirmed":
        raise HTTPException(400, "Already approved")
    if payment.order_id is not None:
        raise HTTPException(400, "This is an order payment, not a deposit request")

    user = (await db.execute(select(User).where(User.id == payment.user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    # Get or create wallet
    wallet = (await db.execute(select(Wallet).where(Wallet.user_id == user.id))).scalar_one_or_none()
    if not wallet:
        wallet = Wallet(user_id=user.id, balance=0)
        db.add(wallet)
        await db.flush()

    before = wallet.balance
    wallet.balance += payment.amount
    wallet.total_deposited += payment.amount

    # Record transaction
    db.add(WalletTransaction(
        wallet_id=wallet.id, type="deposit", amount=payment.amount,
        balance_before=before, balance_after=wallet.balance,
        description=f"Deposit approved (ref: {payment.tx_note or payment.id})",
        reference_id=str(payment.id),
    ))

    payment.status = "confirmed"
    await db.commit()

    # Notify user
    if user.telegram_id:
        msg = await cms_render(db, "notify_deposit_approved", "en",
                               amount=f"{payment.amount:.2f}",
                               method=payment.method_code,
                               balance=f"{wallet.balance:.2f}",
                               reference=payment.tx_note or 'N/A')
        if not msg:
            # Fallback message if CMS template doesn't exist
            msg = (
                f"✅ <b>Deposit Approved!</b>\n\n"
                f"💰 Amount: <b>${payment.amount:.2f}</b>\n"
                f"🆔 Reference: <code>{payment.tx_note or 'N/A'}</code>\n"
                f"💵 New Balance: <b>${wallet.balance:.2f}</b>\n\n"
                f"Your wallet has been credited! 🎉"
            )
        await send_telegram(user.telegram_id, msg)

    logger.info(f"[Deposit] ✅ Approved ${payment.amount} for {user.username} (TG:{user.telegram_id})")

    # Admin group notification
    admin_gid = settings.ADMIN_GROUP_ID
    if admin_gid:
        await send_telegram(int(admin_gid), (
            f"✅ <b>Deposit Confirmed</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤  <b>{user.username or user.full_name or '—'}</b>\n"
            f"🆔  <code>{user.telegram_id}</code>\n\n"
            f"💰  <b>${payment.amount:.2f}</b>  ·  {payment.method_code}\n"
            f"🔖  Ref: <code>{payment.tx_note or 'N/A'}</code>\n"
            f"💎  New Balance: <b>${wallet.balance:.2f}</b>\n\n"
            f"#deposit #confirmed ✅"
        ))

    return {"success": True, "message": f"Deposit ${payment.amount:.2f} approved", "balance": wallet.balance}


@router.post("/{payment_id}/reject")
async def reject_deposit(
    payment_id: str,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    """Reject a deposit request and notify user."""
    payment = (await db.execute(
        select(Payment).where(Payment.id == uuid.UUID(payment_id))
    )).scalar_one_or_none()
    if not payment:
        raise HTTPException(404, "Payment not found")
    if payment.status == "confirmed":
        raise HTTPException(400, "Cannot reject an approved payment")

    payment.status = "failed"
    await db.commit()

    user = (await db.execute(select(User).where(User.id == payment.user_id))).scalar_one_or_none()
    if user and user.telegram_id:
        msg = await cms_render(db, "notify_deposit_rejected", "en",
                               amount=f"{payment.amount:.2f}",
                               method=payment.method_code,
                               reference=payment.tx_note or 'N/A')
        if not msg:
            msg = (
                f"❌ <b>Deposit Rejected</b>\n\n"
                f"💰 Amount: <b>${payment.amount:.2f}</b>\n"
                f"🆔 Reference: <code>{payment.tx_note or 'N/A'}</code>\n\n"
                f"Your deposit request was rejected. Contact support for details."
            )
        await send_telegram(user.telegram_id, msg)

    # Admin group notification
    admin_gid = settings.ADMIN_GROUP_ID
    if admin_gid:
        uname = (user.username or user.full_name or '—') if user else '—'
        uid = user.telegram_id if user else '—'
        await send_telegram(int(admin_gid), (
            f"❌ <b>Deposit Rejected</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤  <b>{uname}</b>\n"
            f"🆔  <code>{uid}</code>\n\n"
            f"💵  <b>${payment.amount:.2f}</b>  ·  {payment.method_code}\n"
            f"🔖  Ref: <code>{payment.tx_note or 'N/A'}</code>\n\n"
            f"#deposit #rejected"
        ))

    return {"success": True, "message": "Deposit rejected"}


@router.put("/{payment_id}/verify")
async def verify_payment(
    payment_id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    payment = (await db.execute(
        select(Payment).where(Payment.id == uuid.UUID(payment_id))
    )).scalar_one_or_none()
    if not payment:
        raise HTTPException(404, "Payment not found")
    payment.status = "confirmed"
    await db.commit()
    return {"success": True}


class BulkDeletePaymentsIn(BaseModel):
    ids: list[str]


@router.delete("/bulk")
async def bulk_delete_payments(
    data: BulkDeletePaymentsIn, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    deleted = 0
    for pid in data.ids:
        try:
            payment = (await db.execute(select(Payment).where(Payment.id == uuid.UUID(pid)))).scalar_one_or_none()
            if payment:
                await db.delete(payment)
                deleted += 1
        except Exception:
            continue
    await db.commit()
    return {"success": True, "deleted": deleted}
