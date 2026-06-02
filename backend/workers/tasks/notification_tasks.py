"""Notification tasks — send Telegram messages, alerts"""
import logging
import requests
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

from workers.celery_app import app
from core.config import settings

logger = logging.getLogger(__name__)

SYNC_DB_URL = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2").replace("postgresql+psycopg2", "postgresql")
engine = create_engine(SYNC_DB_URL, pool_size=2)


@app.task(name="workers.tasks.notification_tasks.send_telegram_message")
def send_telegram_message(chat_id: int, text: str, parse_mode: str = "HTML"):
    """Send a Telegram message via bot API"""
    try:
        url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }, timeout=10)
        resp.raise_for_status()
        return {"success": True, "chat_id": chat_id}
    except Exception as e:
        logger.error(f"Telegram send error: {e}")
        return {"error": str(e)}


@app.task(name="workers.tasks.notification_tasks.notify_admin_new_order")
def notify_admin_new_order(order_id: str):
    """Notify admin of a new order"""
    from models.order import Order
    from models.user import User
    import uuid

    with Session(engine) as session:
        order = session.execute(
            select(Order).where(Order.id == uuid.UUID(order_id))
        ).scalar_one_or_none()
        if not order:
            return

        user = session.execute(
            select(User).where(User.id == order.user_id)
        ).scalar_one_or_none()

        text = (
            f"🆕 <b>New Order!</b>\n\n"
            f"📦 Order: <b>{order.order_number}</b>\n"
            f"👤 User: @{user.username or user.telegram_id}\n"
            f"💰 Amount: <b>${round(float(order.final_amount), 2)}</b>\n"
            f"💳 Payment: {order.payment_method or 'N/A'}\n"
            f"📊 Status: {order.status}"
        )

        # Send to all admin IDs
        admin_ids = settings.ADMIN_IDS.split(",") if settings.ADMIN_IDS else []
        for admin_id in admin_ids:
            admin_id = admin_id.strip()
            if admin_id:
                send_telegram_message.delay(int(admin_id), text)


@app.task(name="workers.tasks.notification_tasks.notify_admin_new_ticket")
def notify_admin_new_ticket(ticket_subject: str, username: str):
    """Notify admin of a new support ticket"""
    text = (
        f"🆘 <b>New Support Ticket</b>\n\n"
        f"👤 From: @{username}\n"
        f"📝 Subject: {ticket_subject}"
    )
    admin_ids = settings.ADMIN_IDS.split(",") if settings.ADMIN_IDS else []
    for admin_id in admin_ids:
        admin_id = admin_id.strip()
        if admin_id:
            send_telegram_message.delay(int(admin_id), text)


@app.task(name="workers.tasks.notification_tasks.notify_user_order_delivered")
def notify_user_order_delivered(telegram_id: int, order_number: str, delivery_data: str):
    """Notify user that their order was delivered"""
    text = (
        f"✅ <b>Order Delivered!</b>\n\n"
        f"📦 Order: <b>{order_number}</b>\n\n"
        f"📋 Your data:\n<code>{delivery_data}</code>\n\n"
        f"Thank you for shopping! 🎉"
    )
    send_telegram_message.delay(telegram_id, text)


@app.task(name="workers.tasks.notification_tasks.notify_payment_confirmed")
def notify_payment_confirmed(telegram_id: int, order_number: str, amount: float):
    """Notify user that payment was confirmed"""
    text = (
        f"✅ <b>Payment Confirmed!</b>\n\n"
        f"📦 Order: <b>{order_number}</b>\n"
        f"💰 Amount: <b>${amount}</b>\n\n"
        f"Your order is being processed..."
    )
    send_telegram_message.delay(telegram_id, text)
