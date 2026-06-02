"""Reseller Admin API — Manage reseller API keys, wallets, wholesale prices"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel as PydanticBase
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from core.database import get_db
from core.security import get_current_admin
from models.reseller import ResellerKey, ResellerTransaction
from models.catalog import Product, ProductPrice

router = APIRouter(prefix="/resellers", tags=["resellers"])


# ─── List & Stats ────────────────────────────────────

@router.get("")
async def list_resellers(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(
        select(ResellerKey).where(ResellerKey.is_deleted == False).order_by(desc(ResellerKey.created_at))
    )
    items = []
    for r in result.scalars().all():
        items.append({
            "id": str(r.id),
            "name": r.name,
            "api_key": r.api_key,
            "is_active": r.is_active,
            "balance": round(r.balance, 2),
            "total_deposited": round(r.total_deposited, 2),
            "total_spent": round(r.total_spent, 2),
            "total_orders": r.total_orders,
            "rate_limit": r.rate_limit,
            "permissions": r.permissions,
            "contact": r.contact,
            "notes": r.notes,
            "created_at": r.created_at.isoformat(),
        })
    return {"resellers": items}


@router.get("/stats")
async def reseller_stats(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    total = (await db.execute(
        select(func.count(ResellerKey.id)).where(ResellerKey.is_deleted == False)
    )).scalar() or 0

    active = (await db.execute(
        select(func.count(ResellerKey.id)).where(ResellerKey.is_deleted == False, ResellerKey.is_active == True)
    )).scalar() or 0

    total_balance = (await db.execute(
        select(func.coalesce(func.sum(ResellerKey.balance), 0)).where(ResellerKey.is_deleted == False)
    )).scalar() or 0

    total_revenue = (await db.execute(
        select(func.coalesce(func.sum(ResellerKey.total_spent), 0)).where(ResellerKey.is_deleted == False)
    )).scalar() or 0

    total_orders = (await db.execute(
        select(func.coalesce(func.sum(ResellerKey.total_orders), 0)).where(ResellerKey.is_deleted == False)
    )).scalar() or 0

    return {
        "total_resellers": total,
        "active_resellers": active,
        "total_balance": round(float(total_balance), 2),
        "total_revenue": round(float(total_revenue), 2),
        "total_orders": int(total_orders),
    }


# ─── CRUD ─────────────────────────────────────────────

class CreateReseller(PydanticBase):
    name: str
    contact: str = ""
    notes: str = ""
    rate_limit: int = 60

@router.post("")
async def create_reseller(data: CreateReseller, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    key = ResellerKey(
        name=data.name,
        api_key=ResellerKey.generate_key(),
        permissions=["products.read", "purchase", "balance.read", "orders.read"],
        contact=data.contact,
        notes=data.notes,
        rate_limit=data.rate_limit,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return {
        "success": True,
        "reseller": {
            "id": str(key.id),
            "name": key.name,
            "api_key": key.api_key,
        }
    }


class UpdateReseller(PydanticBase):
    name: str | None = None
    is_active: bool | None = None
    rate_limit: int | None = None
    contact: str | None = None
    notes: str | None = None

@router.put("/{reseller_id}")
async def update_reseller(
    reseller_id: str, data: UpdateReseller,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    reseller = (await db.execute(
        select(ResellerKey).where(ResellerKey.id == uuid.UUID(reseller_id))
    )).scalar_one_or_none()
    if not reseller:
        raise HTTPException(404, "Reseller not found")

    if data.name is not None: reseller.name = data.name
    if data.is_active is not None: reseller.is_active = data.is_active
    if data.rate_limit is not None: reseller.rate_limit = data.rate_limit
    if data.contact is not None: reseller.contact = data.contact
    if data.notes is not None: reseller.notes = data.notes

    await db.commit()
    return {"success": True}


@router.delete("/{reseller_id}")
async def delete_reseller(
    reseller_id: str,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    reseller = (await db.execute(
        select(ResellerKey).where(ResellerKey.id == uuid.UUID(reseller_id))
    )).scalar_one_or_none()
    if not reseller:
        raise HTTPException(404, "Reseller not found")
    reseller.is_deleted = True
    reseller.is_active = False
    await db.commit()
    return {"success": True}


@router.post("/{reseller_id}/regenerate")
async def regenerate_key(
    reseller_id: str,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    reseller = (await db.execute(
        select(ResellerKey).where(ResellerKey.id == uuid.UUID(reseller_id))
    )).scalar_one_or_none()
    if not reseller:
        raise HTTPException(404, "Reseller not found")
    reseller.api_key = ResellerKey.generate_key()
    await db.commit()
    return {"success": True, "api_key": reseller.api_key}


# ─── Balance Management ──────────────────────────────

class BalanceAction(PydanticBase):
    amount: float
    note: str = ""

@router.post("/{reseller_id}/deposit")
async def deposit(
    reseller_id: str, data: BalanceAction,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    reseller = (await db.execute(
        select(ResellerKey).where(ResellerKey.id == uuid.UUID(reseller_id))
    )).scalar_one_or_none()
    if not reseller:
        raise HTTPException(404, "Reseller not found")

    before = reseller.balance
    reseller.balance += data.amount
    reseller.total_deposited += data.amount

    db.add(ResellerTransaction(
        reseller_id=reseller.id, type="deposit",
        amount=data.amount, balance_before=before, balance_after=reseller.balance,
        description=data.note or f"Admin deposit +${data.amount:.2f}",
    ))
    await db.commit()
    return {"success": True, "balance": round(reseller.balance, 2)}


@router.post("/{reseller_id}/deduct")
async def deduct(
    reseller_id: str, data: BalanceAction,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    reseller = (await db.execute(
        select(ResellerKey).where(ResellerKey.id == uuid.UUID(reseller_id))
    )).scalar_one_or_none()
    if not reseller:
        raise HTTPException(404, "Reseller not found")

    before = reseller.balance
    reseller.balance = max(0, reseller.balance - data.amount)

    db.add(ResellerTransaction(
        reseller_id=reseller.id, type="deduct",
        amount=-data.amount, balance_before=before, balance_after=reseller.balance,
        description=data.note or f"Admin deduction -${data.amount:.2f}",
    ))
    await db.commit()
    return {"success": True, "balance": round(reseller.balance, 2)}


# ─── Transaction History ─────────────────────────────

@router.get("/{reseller_id}/transactions")
async def list_transactions(
    reseller_id: str, page: int = 1, limit: int = 30,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    total = (await db.execute(
        select(func.count(ResellerTransaction.id)).where(
            ResellerTransaction.reseller_id == uuid.UUID(reseller_id),
            ResellerTransaction.is_deleted == False,
        )
    )).scalar() or 0

    result = await db.execute(
        select(ResellerTransaction).where(
            ResellerTransaction.reseller_id == uuid.UUID(reseller_id),
            ResellerTransaction.is_deleted == False,
        ).order_by(desc(ResellerTransaction.created_at))
        .offset((page - 1) * limit).limit(limit)
    )

    txs = []
    for tx in result.scalars().all():
        txs.append({
            "id": str(tx.id),
            "type": tx.type,
            "amount": round(tx.amount, 2),
            "balance_after": round(tx.balance_after, 2),
            "product_name": tx.product_name,
            "quantity": tx.quantity,
            "description": tx.description,
            "created_at": tx.created_at.isoformat(),
        })

    return {"transactions": txs, "total": total, "page": page, "pages": max(1, (total + limit - 1) // limit)}


# ─── Wholesale Price Management ──────────────────────

@router.get("/wholesale-prices")
async def get_wholesale_prices(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(
        select(Product).where(Product.is_deleted == False).order_by(Product.sort_order)
    )
    products = []
    for p in result.scalars().all():
        meta = p.meta or {}
        price_obj = (await db.execute(
            select(ProductPrice).where(ProductPrice.product_id == p.id).order_by(ProductPrice.min_qty)
        )).scalars().first()

        products.append({
            "id": str(p.id),
            "name": p.name,
            "retail_price": round(price_obj.price, 2) if price_obj else 0,
            "wholesale_price": meta.get("wholesale_price"),
        })
    return {"products": products}


class WholesaleUpdate(PydanticBase):
    wholesale_price: float | None = None

@router.put("/wholesale-prices/{product_id}")
async def set_wholesale_price(
    product_id: str, data: WholesaleUpdate,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    product = (await db.execute(
        select(Product).where(Product.id == uuid.UUID(product_id))
    )).scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")

    meta = dict(product.meta or {})
    if data.wholesale_price is not None:
        meta["wholesale_price"] = data.wholesale_price
    else:
        meta.pop("wholesale_price", None)

    product.meta = meta
    flag_modified(product, "meta")
    await db.commit()
    return {"success": True}
