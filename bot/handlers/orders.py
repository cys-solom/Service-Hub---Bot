"""Orders handler — order history — smooth navigation"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
from models.user import User
from models.order import Order, OrderItem
from models.catalog import Product

from keyboards import back_kb

router = Router()

STATUS_ICONS = {
    "waiting_payment": "⏳",
    "pending": "⏳",
    "under_review": "🔍",
    "paid": "✅",
    "delivered": "📦",
    "canceled": "❌",
    "refunded": "💸",
}


@router.message(Command("myorders"))
@router.callback_query(F.data == "menu:orders")
async def show_orders(event, session: AsyncSession, lang: str = "en", **kwargs):
    tg_id = event.from_user.id
    user = (await session.execute(select(User).where(User.telegram_id == tg_id))).scalar_one_or_none()

    orders = (await session.execute(
        select(Order).where(Order.user_id == user.id, Order.is_deleted == False)
        .order_by(desc(Order.created_at)).limit(10)
    )).scalars().all()

    if not orders:
        text = "📦 <b>Order History</b>\n\nNo orders yet."
    else:
        lines = ["📦 <b>ORDER HISTORY</b>\n"]
        for o in orders:
            icon = STATUS_ICONS.get(o.status, "❓")
            date = o.created_at.strftime("%Y-%m-%d %H:%M") if o.created_at else ""

            oi = (await session.execute(
                select(OrderItem).where(OrderItem.order_id == o.id).limit(1)
            )).scalar_one_or_none()

            product_name = ""
            qty = 0
            if oi:
                prod = (await session.execute(
                    select(Product).where(Product.id == oi.product_id)
                )).scalar_one_or_none()
                if prod:
                    product_name = prod.name
                qty = oi.quantity

            lines.append(
                f"{icon} <b>{o.order_number}</b>\n"
                f"   🛍 {product_name or 'N/A'} x{qty}\n"
                f"   💲 ${o.final_amount:.2f} | {o.status.replace('_', ' ').upper()}\n"
                f"   📅 {date}"
            )
        text = "\n\n".join(lines)

    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=back_kb("menu:back", lang))
        except Exception:
            await event.message.answer(text, reply_markup=back_kb("menu:back", lang))
        await event.answer()
    else:
        await event.answer(text, reply_markup=back_kb("menu:back", lang))
