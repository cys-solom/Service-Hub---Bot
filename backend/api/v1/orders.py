"""Orders API — with Auto-Delivery system"""
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.config import settings
from core.security import get_current_admin
from core.telegram import send_telegram
from core.cms import render as cms_render
from models.order import Order, OrderItem
from models.user import User
from models.stock import StockItem
from models.catalog import Product
from models.referral import Referral
from models.wallet import Wallet, WalletTransaction
from models.system import AppSetting

router = APIRouter(prefix="/orders", tags=["orders"])
logger = logging.getLogger(__name__)


class BulkDeleteIn(BaseModel):
    ids: list[str]


@router.delete("/bulk")
async def bulk_delete_orders(data: BulkDeleteIn, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    deleted = 0
    for oid in data.ids:
        try:
            order = (await db.execute(select(Order).where(Order.id == uuid.UUID(oid)))).scalar_one_or_none()
            if order:
                items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
                for item in items:
                    await db.delete(item)
                await db.delete(order)
                deleted += 1
        except Exception:
            continue
    await db.commit()
    return {"success": True, "deleted": deleted}


@router.delete("/{order_id}")
async def delete_order(order_id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    order = (await db.execute(select(Order).where(Order.id == uuid.UUID(order_id)))).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Order not found")
    await db.delete(order)
    items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
    for item in items:
        await db.delete(item)
    await db.commit()
    return {"success": True}


@router.get("")
async def list_orders(
    status: str = "", page: int = 1, limit: int = 20,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    query = select(Order, User).join(User, Order.user_id == User.id).where(Order.is_deleted == False)
    count_q = select(func.count(Order.id)).where(Order.is_deleted == False)

    if status:
        query = query.where(Order.status == status)
        count_q = count_q.where(Order.status == status)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(query.order_by(desc(Order.created_at)).offset((page-1)*limit).limit(limit))

    orders = [{
        "id": str(o.id), "order_number": o.order_number,
        "user_id": str(o.user_id),
        "username": u.username or f"ID:{u.telegram_id}",
        "display_name": " ".join(filter(None, [u.first_name, u.last_name])) or u.username or f"ID:{u.telegram_id}",
        "telegram_id": u.telegram_id,
        "total_amount": round(float(o.total_amount), 2),
        "discount_amount": round(float(o.discount_amount), 2),
        "final_amount": round(float(o.final_amount), 2),
        "currency": o.currency, "status": o.status,
        "payment_method": o.payment_method,
        "coupon_code": o.coupon_code,
        "created_at": o.created_at.isoformat(),
    } for o, u in result.all()]

    return {"orders": orders, "total": total, "page": page, "pages": max(1, (total+limit-1)//limit)}


@router.get("/{order_id}")
async def get_order(
    order_id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    order = (await db.execute(
        select(Order).where(Order.id == uuid.UUID(order_id))
    )).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Order not found")

    # Get user info
    user = (await db.execute(select(User).where(User.id == order.user_id))).scalar_one_or_none()

    items_result = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order.id)
    )
    items = []
    for oi in items_result.scalars().all():
        product = (await db.execute(select(Product).where(Product.id == oi.product_id))).scalar_one_or_none()
        items.append({
            "id": str(oi.id), "product_id": str(oi.product_id),
            "product_name": product.name if product else "Unknown",
            "quantity": oi.quantity, "unit_price": oi.unit_price,
            "total_price": oi.total_price, "status": oi.status,
            "delivered_data": oi.delivered_data,
        })

    return {
        "id": str(order.id), "order_number": order.order_number,
        "user_id": str(order.user_id),
        "telegram_id": user.telegram_id if user else None,
        "username": user.username if user else None,
        "status": order.status, "total_amount": order.total_amount,
        "final_amount": order.final_amount, "currency": order.currency,
        "payment_method": order.payment_method,
        "notes": order.notes, "delivery_data": order.delivery_data,
        "created_at": order.created_at.isoformat(),
        "items": items,
    }


class OrderStatusUpdate(BaseModel):
    status: str


@router.put("/{order_id}/status")
async def update_order_status(
    order_id: str, data: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    order = (await db.execute(
        select(Order).where(Order.id == uuid.UUID(order_id))
    )).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Order not found")

    valid = ["pending", "waiting_payment", "paid", "under_review", "delivered", "canceled", "refunded"]
    if data.status not in valid:
        raise HTTPException(400, f"Invalid status. Must be one of: {valid}")

    # If changing to "delivered" → trigger auto-delivery (same as approve)
    if data.status == "delivered" and order.status != "delivered":
        result = await _auto_deliver_order(db, order)
        if not result["success"]:
            raise HTTPException(400, result.get("error", "Delivery failed"))
        return {"success": True, "status": "delivered", "delivered_count": result["delivered_count"]}

    order.status = data.status
    await db.commit()
    return {"success": True, "status": order.status}


class BulkOrderDeleteIn(BaseModel):
    ids: list[str]


@router.delete("/bulk")
async def bulk_delete_orders(
    data: BulkOrderDeleteIn,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    """Delete multiple orders at once."""
    count = 0
    for oid in data.ids:
        o = (await db.execute(select(Order).where(Order.id == uuid.UUID(oid)))).scalar_one_or_none()
        if o:
            o.is_deleted = True
            count += 1
    await db.commit()
    return {"success": True, "deleted": count}


@router.delete("/{order_id}")
async def delete_order(
    order_id: str,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    """Soft-delete an order."""
    order = (await db.execute(
        select(Order).where(Order.id == uuid.UUID(order_id))
    )).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Order not found")

    order.is_deleted = True
    await db.commit()
    return {"success": True, "message": "Order deleted"}


# ═══════════════════════════════════════════
# AUTO-DELIVERY SYSTEM
# ═══════════════════════════════════════════


async def _auto_deliver_order(db: AsyncSession, order: Order) -> dict:
    """Pull stock items, mark as sold, deliver to user via Telegram.
    
    Returns: {"success": bool, "delivered_count": int, "delivery_data": list}
    """
    user = (await db.execute(select(User).where(User.id == order.user_id))).scalar_one_or_none()
    if not user:
        return {"success": False, "error": "User not found"}

    items = (await db.execute(
        select(OrderItem).where(OrderItem.order_id == order.id)
    )).scalars().all()

    all_delivery = []
    delivered_count = 0

    for oi in items:
        product = (await db.execute(select(Product).where(Product.id == oi.product_id))).scalar_one_or_none()
        product_name = product.name if product else "Product"

        # Fetch available stock items for this product
        stock_result = await db.execute(
            select(StockItem).where(
                StockItem.product_id == oi.product_id,
                StockItem.is_sold == False,
                StockItem.is_deleted == False,
            ).order_by(StockItem.sort_order, StockItem.created_at).limit(oi.quantity)
        )
        stock_items = stock_result.scalars().all()

        if len(stock_items) < oi.quantity:
            return {
                "success": False,
                "error": f"Not enough stock for '{product_name}'. Need {oi.quantity}, have {len(stock_items)}",
            }

        # Mark stock as sold and collect delivery data
        item_delivery = []
        for si in stock_items:
            si.is_sold = True
            si.sold_to = order.user_id
            si.order_id = order.id
            item_delivery.append(si.data)
            delivered_count += 1

        delivery_text = "\n".join(item_delivery)
        oi.delivered_data = delivery_text
        oi.status = "delivered"

        all_delivery.append({
            "product": product_name,
            "quantity": oi.quantity,
            "data": item_delivery,
        })

    order.status = "delivered"
    order.delivery_data = {"items": all_delivery, "auto": True}
    await db.commit()

    # ── Auto-credit referral commission ──
    await _credit_referral(db, order.user_id, order.final_amount)

    # Send delivery to user via Telegram
    if user.telegram_id:
        msg_lines = [
            f"✅ <b>Order #{order.order_number} — Delivered!</b>\n",
            f"━━━━━━━━━━━━━━━",
        ]
        for d in all_delivery:
            msg_lines.append(f"\n📦 <b>{d['product']}</b> x{d['quantity']}:")
            for idx, data in enumerate(d["data"], 1):
                msg_lines.append(f"<code>{data}</code>")

        msg_lines.append(f"\n━━━━━━━━━━━━━━━")
        msg_lines.append(f"💰 Total: <b>${order.final_amount:.2f}</b>")
        msg_lines.append(f"\n⚠️ Save this data! It will not be shown again.")

        await send_telegram(user.telegram_id, "\n".join(msg_lines))

    return {"success": True, "delivered_count": delivered_count, "delivery_data": all_delivery}


@router.post("/{order_id}/approve")
async def approve_order(
    order_id: str,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    """Approve an order and auto-deliver stock items to the customer."""
    order = (await db.execute(
        select(Order).where(Order.id == uuid.UUID(order_id))
    )).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Order not found")

    if order.status == "delivered":
        raise HTTPException(400, "Order already delivered")
    if order.status == "canceled":
        raise HTTPException(400, "Cannot approve a canceled order")

    result = await _auto_deliver_order(db, order)

    if not result["success"]:
        raise HTTPException(400, result.get("error", "Delivery failed"))

    logger.info(f"[AutoDeliver] ✅ Order {order.order_number} delivered ({result['delivered_count']} items)")

    # Admin group notification
    admin_gid = settings.ADMIN_GROUP_ID
    if admin_gid:
        user = (await db.execute(select(User).where(User.id == order.user_id))).scalar_one_or_none()
        uname = (user.username or user.full_name or '—') if user else '—'
        uid = user.telegram_id if user else '—'
        items_text = ''
        for d in result.get('delivery_data', []):
            items_text += f"\n📦  {d['product']} x{d['quantity']}"
        await send_telegram(int(admin_gid), (
            f"✅ <b>Order Delivered</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤  <b>{uname}</b>\n"
            f"🆔  <code>{uid}</code>\n"
            f"🧻  <code>{order.order_number}</code>\n"
            f"{items_text}\n"
            f"💰  <b>${order.final_amount:.2f}</b>\n\n"
            f"#order #delivered ✅"
        ))

    return {
        "success": True,
        "message": f"Order approved & delivered ({result['delivered_count']} items)",
        "delivered_count": result["delivered_count"],
    }


class RejectData(BaseModel):
    reason: str = "Order rejected by admin"


@router.post("/{order_id}/reject")
async def reject_order(
    order_id: str, data: RejectData = RejectData(),
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    """Reject an order and notify the customer."""
    order = (await db.execute(
        select(Order).where(Order.id == uuid.UUID(order_id))
    )).scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Order not found")

    if order.status == "delivered":
        raise HTTPException(400, "Cannot reject a delivered order")

    order.status = "canceled"
    order.notes = data.reason
    await db.commit()

    # Notify user
    user = (await db.execute(select(User).where(User.id == order.user_id))).scalar_one_or_none()
    if user and user.telegram_id:
        msg = await cms_render(db, "notify_order_rejected", "en",
                               order_number=order.order_number,
                               reason=data.reason)
        if msg:
            await send_telegram(user.telegram_id, msg)

    # Admin group notification
    admin_gid = settings.ADMIN_GROUP_ID
    if admin_gid:
        uname = (user.username or user.full_name or '—') if user else '—'
        uid = user.telegram_id if user else '—'
        await send_telegram(int(admin_gid), (
            f"❌ <b>Order Cancelled</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤  <b>{uname}</b>\n"
            f"🆔  <code>{uid}</code>\n"
            f"🧻  <code>{order.order_number}</code>\n"
            f"💰  <b>${order.final_amount:.2f}</b>\n"
            f"📝  {data.reason}\n\n"
            f"#order #cancelled"
        ))

    return {"success": True, "message": "Order rejected"}


async def _credit_referral(db: AsyncSession, user_id, order_amount: float):
    """Credit referrer wallet when an order is delivered (backend side)."""
    try:
        enabled_row = (await db.execute(
            select(AppSetting).where(AppSetting.key == "referral_enabled", AppSetting.is_deleted == False)
        )).scalar_one_or_none()
        if not enabled_row or enabled_row.value != "true":
            return

        auto_row = (await db.execute(
            select(AppSetting).where(AppSetting.key == "referral_auto_credit", AppSetting.is_deleted == False)
        )).scalar_one_or_none()
        if not auto_row or auto_row.value != "true":
            return

        referral = (await db.execute(
            select(Referral).where(
                Referral.referred_id == user_id,
                Referral.is_deleted == False,
                Referral.status == "active",
            )
        )).scalar_one_or_none()
        if not referral:
            return

        commission = round(order_amount * referral.commission_percent / 100, 2)
        if commission <= 0:
            return

        wallet = (await db.execute(
            select(Wallet).where(Wallet.user_id == referral.referrer_id)
        )).scalar_one_or_none()
        if not wallet:
            wallet = Wallet(user_id=referral.referrer_id, balance=0, currency="USD")
            db.add(wallet)
            await db.flush()

        before = wallet.balance
        wallet.balance += commission
        wallet.total_deposited += commission

        db.add(WalletTransaction(
            wallet_id=wallet.id, type="referral_commission", amount=commission,
            balance_before=before, balance_after=wallet.balance,
            description=f"Referral commission ({referral.commission_percent}%) from order ${order_amount:.2f}",
        ))

        referral.total_earned += commission
        referral.total_orders += 1
        await db.commit()

        logger.info(f"[Referral] Credited ${commission:.2f} to referrer (user_id={referral.referrer_id})")

    except Exception as e:
        logger.error(f"[Referral] Commission error: {e}", exc_info=True)

