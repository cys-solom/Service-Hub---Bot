"""Referrals API — Enhanced with settings, per-pair controls, detailed stats"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_admin
from models.referral import Referral
from models.user import User
from models.order import Order
from models.system import AppSetting

router = APIRouter(prefix="/referrals", tags=["referrals"])


def _display_name(u):
    if not u:
        return "N/A"
    parts = [u.first_name or "", u.last_name or ""]
    name = " ".join(p for p in parts if p).strip()
    return name or u.username or "N/A"


# ─── Settings ────────────────────────────────────────

REFERRAL_KEYS = [
    "referral_enabled", "referral_commission_percent",
    "referral_min_order_amount", "referral_auto_credit", "referral_max_invites",
]

@router.get("/settings")
async def get_referral_settings(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(
        select(AppSetting).where(AppSetting.key.in_(REFERRAL_KEYS))
    )
    settings = {s.key: s.value for s in result.scalars().all()}
    return {
        "referral_enabled": settings.get("referral_enabled", "true") == "true",
        "referral_commission_percent": float(settings.get("referral_commission_percent", "5")),
        "referral_min_order_amount": float(settings.get("referral_min_order_amount", "0")),
        "referral_auto_credit": settings.get("referral_auto_credit", "true") == "true",
        "referral_max_invites": int(settings.get("referral_max_invites", "0")),
    }


class ReferralSettingsUpdate(BaseModel):
    referral_enabled: bool | None = None
    referral_commission_percent: float | None = None
    referral_min_order_amount: float | None = None
    referral_auto_credit: bool | None = None
    referral_max_invites: int | None = None

@router.put("/settings")
async def update_referral_settings(
    data: ReferralSettingsUpdate,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    updates = {}
    if data.referral_enabled is not None:
        updates["referral_enabled"] = str(data.referral_enabled).lower()
    if data.referral_commission_percent is not None:
        updates["referral_commission_percent"] = str(data.referral_commission_percent)
    if data.referral_min_order_amount is not None:
        updates["referral_min_order_amount"] = str(data.referral_min_order_amount)
    if data.referral_auto_credit is not None:
        updates["referral_auto_credit"] = str(data.referral_auto_credit).lower()
    if data.referral_max_invites is not None:
        updates["referral_max_invites"] = str(data.referral_max_invites)

    for key, value in updates.items():
        setting = (await db.execute(select(AppSetting).where(AppSetting.key == key))).scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            db.add(AppSetting(key=key, value=value, type="string", group="referral"))

    await db.commit()
    return {"success": True}


# ─── List & Stats ────────────────────────────────────

@router.get("")
async def list_referrals(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(
        select(Referral).where(Referral.is_deleted == False).order_by(desc(Referral.created_at))
    )
    items = []
    for r in result.scalars().all():
        referrer = (await db.execute(select(User).where(User.id == r.referrer_id))).scalar_one_or_none()
        referred = (await db.execute(select(User).where(User.id == r.referred_id))).scalar_one_or_none()

        # Count referred user's delivered orders
        referred_orders = 0
        referred_spent = 0.0
        if referred:
            stats = await db.execute(
                select(func.count(Order.id), func.coalesce(func.sum(Order.final_amount), 0))
                .where(Order.user_id == referred.id, Order.status == "delivered", Order.is_deleted == False)
            )
            row = stats.first()
            if row:
                referred_orders = row[0] or 0
                referred_spent = float(row[1] or 0)

        items.append({
            "id": str(r.id),
            "referrer_id": str(r.referrer_id),
            "referrer_name": _display_name(referrer),
            "referrer_username": referrer.username if referrer else "N/A",
            "referrer_telegram_id": referrer.telegram_id if referrer else None,
            "referred_id": str(r.referred_id),
            "referred_name": _display_name(referred),
            "referred_username": referred.username if referred else "N/A",
            "referred_telegram_id": referred.telegram_id if referred else None,
            "referred_orders": referred_orders,
            "referred_spent": round(referred_spent, 2),
            "commission_percent": r.commission_percent,
            "total_earned": round(r.total_earned, 2),
            "total_orders": r.total_orders,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
        })
    return {"referrals": items}


@router.get("/stats")
async def referral_stats(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    total = (await db.execute(
        select(func.count(Referral.id)).where(Referral.is_deleted == False)
    )).scalar() or 0

    active = (await db.execute(
        select(func.count(Referral.id)).where(Referral.is_deleted == False, Referral.status == "active")
    )).scalar() or 0

    total_earned = (await db.execute(
        select(func.coalesce(func.sum(Referral.total_earned), 0)).where(Referral.is_deleted == False)
    )).scalar() or 0

    total_orders = (await db.execute(
        select(func.coalesce(func.sum(Referral.total_orders), 0)).where(Referral.is_deleted == False)
    )).scalar() or 0

    # Top referrers
    top_result = await db.execute(
        select(
            Referral.referrer_id,
            func.count(Referral.id).label("count"),
            func.coalesce(func.sum(Referral.total_earned), 0).label("earned"),
        )
        .where(Referral.is_deleted == False)
        .group_by(Referral.referrer_id)
        .order_by(desc("count"))
        .limit(5)
    )
    top_referrers = []
    for row in top_result.all():
        user = (await db.execute(select(User).where(User.id == row[0]))).scalar_one_or_none()
        top_referrers.append({
            "user_id": str(row[0]),
            "name": _display_name(user),
            "username": user.username if user else "N/A",
            "telegram_id": user.telegram_id if user else None,
            "referral_count": row[1],
            "total_earned": round(float(row[2]), 2),
        })

    return {
        "total_referrals": total,
        "active_referrals": active,
        "total_earned": round(float(total_earned), 2),
        "total_orders": int(total_orders),
        "top_referrers": top_referrers,
    }


# ─── Per-pair Controls ───────────────────────────────

class CommissionUpdate(BaseModel):
    commission_percent: float

@router.put("/{referral_id}/commission")
async def update_commission(
    referral_id: str, data: CommissionUpdate,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    ref = (await db.execute(
        select(Referral).where(Referral.id == uuid.UUID(referral_id))
    )).scalar_one_or_none()
    if not ref:
        raise HTTPException(404, "Referral not found")
    ref.commission_percent = data.commission_percent
    await db.commit()
    return {"success": True}


class StatusUpdate(BaseModel):
    status: str  # active, inactive

@router.put("/{referral_id}/status")
async def update_status(
    referral_id: str, data: StatusUpdate,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    ref = (await db.execute(
        select(Referral).where(Referral.id == uuid.UUID(referral_id))
    )).scalar_one_or_none()
    if not ref:
        raise HTTPException(404, "Referral not found")
    ref.status = data.status
    await db.commit()
    return {"success": True}


@router.delete("/bulk")
async def bulk_delete_referrals(
    data: dict,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    ids = data.get("ids", [])
    if not ids:
        raise HTTPException(400, "No IDs provided")
    for rid in ids:
        ref = (await db.execute(
            select(Referral).where(Referral.id == uuid.UUID(rid))
        )).scalar_one_or_none()
        if ref:
            ref.is_deleted = True
    await db.commit()
    return {"success": True, "deleted": len(ids)}
