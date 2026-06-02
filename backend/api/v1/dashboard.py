"""Dashboard stats API"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_admin
from models.user import User
from models.order import Order
from models.stock import StockItem
from models.catalog import Category, Product
from models.support import SupportTicket

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_users = (await db.execute(select(func.count(User.id)).where(User.is_deleted == False))).scalar() or 0
    total_orders = (await db.execute(select(func.count(Order.id)))).scalar() or 0
    total_revenue = round(float((await db.execute(
        select(func.coalesce(func.sum(Order.final_amount), 0)).where(Order.status == "delivered")
    )).scalar() or 0), 2)
    today_revenue = round(float((await db.execute(
        select(func.coalesce(func.sum(Order.final_amount), 0))
        .where(Order.status == "delivered", Order.created_at >= today)
    )).scalar() or 0), 2)
    today_orders = (await db.execute(
        select(func.count(Order.id)).where(Order.created_at >= today)
    )).scalar() or 0
    stock_available = (await db.execute(
        select(func.count(StockItem.id)).where(StockItem.is_sold == False, StockItem.is_deleted == False)
    )).scalar() or 0
    pending_orders = (await db.execute(
        select(func.count(Order.id)).where(Order.status.in_(["pending", "waiting_payment"]))
    )).scalar() or 0
    open_tickets = (await db.execute(
        select(func.count(SupportTicket.id)).where(SupportTicket.status.in_(["open", "in_progress"]))
    )).scalar() or 0
    categories_count = (await db.execute(
        select(func.count(Category.id)).where(Category.is_deleted == False)
    )).scalar() or 0
    products_count = (await db.execute(
        select(func.count(Product.id)).where(Product.is_deleted == False)
    )).scalar() or 0

    # Recent orders
    recent_result = await db.execute(
        select(Order, User)
        .join(User, Order.user_id == User.id)
        .order_by(desc(Order.created_at))
        .limit(10)
    )
    recent_orders = [{
        "id": str(o.id), "order_number": o.order_number,
        "username": u.username or f"ID:{u.telegram_id}",
        "total": round(float(o.final_amount), 2),
        "status": o.status,
        "date": o.created_at.isoformat(),
    } for o, u in recent_result.all()]

    # Low stock products
    low_stock_q = (
        select(Product.name, func.count(StockItem.id).label("available"))
        .join(StockItem, StockItem.product_id == Product.id)
        .where(StockItem.is_sold == False, StockItem.is_deleted == False)
        .group_by(Product.id, Product.name)
        .having(func.count(StockItem.id) < 5)
    )
    low_stock_result = await db.execute(low_stock_q)
    low_stock = [{"name": r.name, "available": r.available} for r in low_stock_result.all()]

    return {
        "total_users": total_users, "total_orders": total_orders,
        "total_revenue": total_revenue, "today_revenue": today_revenue,
        "today_orders": today_orders, "stock_available": stock_available,
        "pending_orders": pending_orders, "open_tickets": open_tickets,
        "categories_count": categories_count, "products_count": products_count,
        "recent_orders": recent_orders, "low_stock": low_stock,
    }


@router.get("/chart")
async def get_chart_data(
    days: int = 14, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    start = datetime.now(timezone.utc) - timedelta(days=days)
    day_col = func.date_trunc("day", Order.created_at).label("day")
    result = await db.execute(
        select(
            day_col,
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(Order.final_amount), 0).label("revenue"),
        )
        .where(Order.created_at >= start)
        .group_by(day_col).order_by(day_col)
    )
    rows = result.all()
    return {
        "labels": [r.day.strftime("%m/%d") for r in rows] or ["No data"],
        "orders": [r.orders for r in rows] or [0],
        "revenue": [round(float(r.revenue), 2) for r in rows] or [0],
    }
