"""App Settings API"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_admin
from models.system import AppSetting

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("")
async def list_settings(group: str = "", db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    query = select(AppSetting).where(AppSetting.is_deleted == False)
    if group: query = query.where(AppSetting.group == group)
    result = await db.execute(query.order_by(AppSetting.group, AppSetting.key))
    return {"settings": [{
        "id": str(s.id), "key": s.key, "value": s.value,
        "value_json": s.value_json, "type": s.type,
        "group": s.group, "description": s.description,
    } for s in result.scalars().all()]}

class SettingUpdate(BaseModel):
    value: Optional[str] = None
    value_json: Optional[dict] = None

@router.put("/{key}")
async def update_setting(key: str, data: SettingUpdate,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    setting = (await db.execute(select(AppSetting).where(AppSetting.key == key))).scalar_one_or_none()
    if not setting:
        setting = AppSetting(key=key, value=data.value, value_json=data.value_json, type="string")
        db.add(setting)
    else:
        if data.value is not None: setting.value = data.value
        if data.value_json is not None: setting.value_json = data.value_json
    await db.commit()
    return {"success": True}


# ─── Dashboard Reset / Undo ──────────────────────────

@router.post("/reset-dashboard")
async def reset_dashboard(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    """Soft-delete all transactional data (orders, payments, users, wallets, stock, support, referrals).
    Products, categories, settings, and admins are preserved."""
    import json
    from datetime import datetime, timezone
    from models.order import Order, OrderItem
    from models.payment import Payment
    from models.user import User
    from models.wallet import Wallet, WalletTransaction
    from models.stock import StockItem
    from models.support import SupportTicket
    from models.referral import Referral
    from models.coupon import Coupon

    counts = {}

    # Orders + OrderItems
    orders = (await db.execute(select(Order))).scalars().all()
    counts["orders"] = len(orders)
    for o in orders:
        await db.delete(o)
    order_items = (await db.execute(select(OrderItem))).scalars().all()
    counts["order_items"] = len(order_items)
    for oi in order_items:
        await db.delete(oi)

    # Payments
    payments = (await db.execute(select(Payment))).scalars().all()
    counts["payments"] = len(payments)
    for p in payments:
        await db.delete(p)

    # Wallet Transactions
    txns = (await db.execute(select(WalletTransaction))).scalars().all()
    counts["wallet_transactions"] = len(txns)
    for t in txns:
        await db.delete(t)

    # Wallets — reset balance to 0
    wallets = (await db.execute(select(Wallet))).scalars().all()
    counts["wallets_reset"] = len(wallets)
    for w in wallets:
        w.balance = 0
        w.total_deposited = 0
        w.total_spent = 0

    # Users — reset stats (keep accounts)
    users = (await db.execute(select(User))).scalars().all()
    counts["users_reset"] = len(users)
    for u in users:
        u.total_spent = 0
        u.total_orders = 0

    # Stock — delete sold items only
    sold_stock = (await db.execute(select(StockItem).where(StockItem.is_sold == True))).scalars().all()
    counts["sold_stock"] = len(sold_stock)
    for s in sold_stock:
        await db.delete(s)

    # Support tickets
    tickets = (await db.execute(select(SupportTicket))).scalars().all()
    counts["tickets"] = len(tickets)
    for t in tickets:
        await db.delete(t)

    # Referrals — reset earnings
    referrals = (await db.execute(select(Referral))).scalars().all()
    counts["referrals"] = len(referrals)
    for r in referrals:
        r.total_earned = 0
        r.total_orders = 0

    # Coupons — reset usage
    coupons = (await db.execute(select(Coupon))).scalars().all()
    for c in coupons:
        c.used_count = 0

    # Save reset snapshot for undo
    snapshot = AppSetting(
        key="last_reset_snapshot",
        value=json.dumps(counts),
        value_json={"counts": counts, "timestamp": datetime.now(timezone.utc).isoformat()},
        type="json",
        group="system",
        description="Last dashboard reset snapshot",
    )
    existing = (await db.execute(select(AppSetting).where(AppSetting.key == "last_reset_snapshot"))).scalar_one_or_none()
    if existing:
        existing.value = json.dumps(counts)
        existing.value_json = {"counts": counts, "timestamp": datetime.now(timezone.utc).isoformat()}
    else:
        db.add(snapshot)

    await db.commit()

    total = sum(v for v in counts.values())
    return {"success": True, "message": f"Dashboard reset — {total} records affected", "counts": counts}


@router.get("/reset-status")
async def reset_status(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    """Check if there's a recent reset that can be referenced."""
    snapshot = (await db.execute(select(AppSetting).where(AppSetting.key == "last_reset_snapshot"))).scalar_one_or_none()
    if not snapshot or not snapshot.value_json:
        return {"has_reset": False}
    return {"has_reset": True, "data": snapshot.value_json}
