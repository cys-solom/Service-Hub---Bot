"""Coupons API — with product assignment"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_admin
from models.coupon import Coupon
from models.catalog import Product

router = APIRouter(prefix="/coupons", tags=["coupons"])


class CouponIn(BaseModel):
    code: str
    type: str = "percent"
    value: float
    min_order: float = 0
    max_discount: Optional[float] = None
    max_uses: int = 0
    is_active: bool = True
    description: Optional[str] = None
    product_ids: list[str] = []  # List of product IDs this coupon applies to


@router.get("")
async def list_coupons(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(Coupon).where(Coupon.is_deleted == False))

    coupons_list = []
    for c in result.scalars().all():
        # Get product names for display
        product_names = []
        product_ids = []
        if c.applies_to and isinstance(c.applies_to, dict) and "product_ids" in c.applies_to:
            product_ids = c.applies_to["product_ids"]
            for pid in product_ids:
                try:
                    p = (await db.execute(
                        select(Product.name).where(Product.id == uuid.UUID(pid))
                    )).scalar_one_or_none()
                    if p:
                        product_names.append(p)
                except Exception:
                    pass

        coupons_list.append({
            "id": str(c.id), "code": c.code, "type": c.type, "value": c.value,
            "min_order": c.min_order, "max_discount": c.max_discount,
            "max_uses": c.max_uses, "used_count": c.used_count,
            "is_active": c.is_active, "description": c.description,
            "product_ids": product_ids,
            "product_names": product_names,
            "applies_to_all": len(product_ids) == 0,
        })

    return {"coupons": coupons_list}


@router.post("")
async def create_coupon(data: CouponIn, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    applies_to = None
    if data.product_ids:
        applies_to = {"product_ids": data.product_ids}

    coupon = Coupon(
        code=data.code, type=data.type, value=data.value,
        min_order=data.min_order, max_discount=data.max_discount,
        max_uses=data.max_uses, is_active=data.is_active,
        description=data.description, applies_to=applies_to,
    )
    db.add(coupon)
    await db.commit()
    return {"success": True, "id": str(coupon.id)}


@router.put("/{coupon_id}")
async def update_coupon(coupon_id: str, data: CouponIn, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    coupon = (await db.execute(select(Coupon).where(Coupon.id == uuid.UUID(coupon_id)))).scalar_one_or_none()
    if not coupon:
        raise HTTPException(404, "Coupon not found")

    coupon.code = data.code
    coupon.type = data.type
    coupon.value = data.value
    coupon.min_order = data.min_order
    coupon.max_discount = data.max_discount
    coupon.max_uses = data.max_uses
    coupon.is_active = data.is_active
    coupon.description = data.description

    if data.product_ids:
        coupon.applies_to = {"product_ids": data.product_ids}
    else:
        coupon.applies_to = None

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(coupon, "applies_to")
    await db.commit()
    return {"success": True}


@router.delete("/{coupon_id}")
async def delete_coupon(coupon_id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    coupon = (await db.execute(select(Coupon).where(Coupon.id == uuid.UUID(coupon_id)))).scalar_one_or_none()
    if not coupon:
        raise HTTPException(404, "Not found")
    coupon.is_deleted = True
    await db.commit()
    return {"success": True}
