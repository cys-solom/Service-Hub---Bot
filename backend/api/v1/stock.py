"""Stock CRUD API — bulk import/export, reserve, restore"""
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.config import settings
from core.security import get_current_admin
from core.telegram import send_telegram
from models.stock import StockItem
from models.catalog import Product

router = APIRouter(prefix="/stock", tags=["stock"])
logger = logging.getLogger(__name__)


class StockAddBulk(BaseModel):
    product_id: str
    items: list[str]  # Each line = one stock item
    format: str = "plain"  # plain, json


@router.get("")
async def list_stock(
    product_id: Optional[str] = None,
    is_sold: Optional[bool] = None,
    page: int = 1, limit: int = 50,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    query = select(StockItem).where(StockItem.is_deleted == False)
    count_q = select(func.count(StockItem.id)).where(StockItem.is_deleted == False)

    if product_id:
        pid = uuid.UUID(product_id)
        query = query.where(StockItem.product_id == pid)
        count_q = count_q.where(StockItem.product_id == pid)
    if is_sold is not None:
        query = query.where(StockItem.is_sold == is_sold)
        count_q = count_q.where(StockItem.is_sold == is_sold)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(query.order_by(StockItem.created_at.desc()).offset((page-1)*limit).limit(limit))
    items = result.scalars().all()

    return {
        "items": [{
            "id": str(i.id), "product_id": str(i.product_id),
            "data": i.data,
            "is_sold": i.is_sold, "is_reserved": i.is_reserved,
            "batch_id": i.batch_id,
            "sold_to": str(i.sold_to) if i.sold_to else None,
            "created_at": i.created_at.isoformat(),
            "updated_at": i.updated_at.isoformat() if i.updated_at else None,
        } for i in items],
        "total": total, "page": page,
        "pages": max(1, (total + limit - 1) // limit),
    }


@router.post("/bulk")
async def add_stock_bulk(
    data: StockAddBulk, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    product = (await db.execute(
        select(Product).where(Product.id == uuid.UUID(data.product_id))
    )).scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")

    batch_id = str(uuid.uuid4())[:8]
    count = 0
    for line in data.items:
        line = line.strip()
        if not line:
            continue
        db.add(StockItem(
            product_id=product.id, data=line,
            is_sold=False, batch_id=batch_id,
        ))
        count += 1

    await db.commit()

    # Get total stock count after adding
    total_stock = (await db.execute(
        select(func.count(StockItem.id)).where(
            StockItem.product_id == product.id,
            StockItem.is_sold == False,
            StockItem.is_deleted == False,
        )
    )).scalar() or 0

    # Build notification via CMS or fallback
    try:
        from core.cms import render as cms_render
        msg = await cms_render(db, "notify_stock_added", "en",
                               product_name=product.name,
                               added_count=str(count),
                               total_stock=str(total_stock))
    except Exception as e:
        logger.error(f"[Stock] CMS render failed: {e}")
        msg = ""
    if not msg:
        msg = (
            f"⚡️ <b>New Stock Available!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"📦  <b>{product.name}</b>\n\n"
            f"➕  Added: <b>{count}</b> item{'s' if count > 1 else ''}\n"
            f"📊  In Stock: <b>{total_stock}</b> available\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🛒 <b>Order now before it's gone!</b>"
        )

    # Broadcast to all bot users
    from models.user import User
    try:
        all_users = (await db.execute(
            select(User).where(User.is_banned == False, User.is_deleted == False)
        )).scalars().all()
        logger.info(f"[Stock] Broadcasting to {len(all_users)} users...")
        sent = 0
        for u in all_users:
            try:
                await send_telegram(u.telegram_id, msg)
                sent += 1
            except Exception as ue:
                logger.warning(f"[Stock] Failed to send to {u.telegram_id}: {ue}")
        logger.info(f"[Stock] Broadcast sent to {sent}/{len(all_users)} users")
    except Exception as e:
        logger.error(f"[Stock] Broadcast FAILED: {e}")
        sent = 0
        all_users = []

    # Send to admin group (with batch for admin reference)
    admin_gid = settings.ADMIN_GROUP_ID
    if admin_gid:
        admin_msg = (
            f"📦 <b>Stock Added</b>  ·  <code>{batch_id}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"🏷  <b>{product.name}</b>\n"
            f"➕  <b>{count}</b> items  →  📊 <b>{total_stock}</b> total\n"
            f"📣  Broadcast: {sent}/{len(all_users)} users\n\n"
            f"#stock #added"
        )
        await send_telegram(int(admin_gid), admin_msg)

    logger.info(f"[Stock] ✅ Added {count} items to '{product.name}' (total: {total_stock})")
    return {"success": True, "added": count, "batch_id": batch_id, "total_stock": total_stock}


class StockAddSingle(BaseModel):
    product_id: str
    data: str


@router.post("/single")
async def add_stock_single(
    body: StockAddSingle, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    product = (await db.execute(
        select(Product).where(Product.id == uuid.UUID(body.product_id))
    )).scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")
    item = StockItem(product_id=product.id, data=body.data.strip(), is_sold=False, batch_id="manual")
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "id": str(item.id)}


@router.get("/export")
async def export_stock(
    product_id: str, include_sold: bool = False,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    query = select(StockItem).where(
        StockItem.product_id == uuid.UUID(product_id),
        StockItem.is_deleted == False,
    )
    if not include_sold:
        query = query.where(StockItem.is_sold == False)

    result = await db.execute(query.order_by(StockItem.created_at))
    items = result.scalars().all()
    return {
        "items": [i.data for i in items],
        "count": len(items),
    }


class StockItemUpdate(BaseModel):
    data: str


class BulkDeleteStock(BaseModel):
    ids: list[str]


@router.get("/summary")
async def stock_summary(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    """Get stock counts per product — fast single query"""
    result = await db.execute(
        select(
            StockItem.product_id,
            func.count(StockItem.id).label("total"),
            func.count(StockItem.id).filter(StockItem.is_sold == False, StockItem.is_reserved == False).label("available"),
            func.count(StockItem.id).filter(StockItem.is_sold == True).label("sold"),
            func.count(StockItem.id).filter(StockItem.is_reserved == True).label("reserved"),
        )
        .where(StockItem.is_deleted == False)
        .group_by(StockItem.product_id)
    )
    summary = {}
    for row in result.all():
        summary[str(row.product_id)] = {
            "total": row.total, "available": row.available,
            "sold": row.sold, "reserved": row.reserved,
        }
    return {"summary": summary}


@router.delete("/bulk")
async def delete_stock_bulk(
    data: BulkDeleteStock, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    uuids = [uuid.UUID(i) for i in data.ids]
    for uid in uuids:
        item = (await db.execute(select(StockItem).where(StockItem.id == uid))).scalar_one_or_none()
        if item:
            item.is_deleted = True
    await db.commit()
    return {"success": True, "deleted": len(uuids)}


@router.delete("/sold")
async def delete_sold_stock(
    product_id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    """Soft-delete all sold stock items for a product"""
    pid = uuid.UUID(product_id)
    result = await db.execute(
        select(StockItem).where(
            StockItem.product_id == pid,
            StockItem.is_sold == True,
            StockItem.is_deleted == False,
        )
    )
    items = result.scalars().all()
    count = 0
    for item in items:
        item.is_deleted = True
        count += 1
    await db.commit()
    return {"success": True, "deleted": count}


# ── Parametric routes MUST come LAST ──
@router.post("/{item_id}/restore")
async def restore_stock_item(
    item_id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    item = (await db.execute(
        select(StockItem).where(StockItem.id == uuid.UUID(item_id))
    )).scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Stock item not found")
    item.is_sold = False
    item.sold_to = None
    item.order_id = None
    item.is_reserved = False
    await db.commit()
    return {"success": True}


@router.put("/{item_id}")
async def update_stock_item(
    item_id: str, body: StockItemUpdate,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    item = (await db.execute(
        select(StockItem).where(StockItem.id == uuid.UUID(item_id))
    )).scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Stock item not found")
    item.data = body.data.strip()
    await db.commit()
    return {"success": True}


@router.delete("/{item_id}")
async def delete_stock_item(
    item_id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    item = (await db.execute(
        select(StockItem).where(StockItem.id == uuid.UUID(item_id))
    )).scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Stock item not found")
    item.is_deleted = True
    await db.commit()
    return {"success": True}

