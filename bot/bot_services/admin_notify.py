# -*- coding: utf-8 -*-
"""Admin Notification Service — Premium styled bot event notifications."""
import logging
from datetime import datetime
from aiogram import Bot

logger = logging.getLogger(__name__)

_bot: Bot = None
_chat_id: str = None


def init(bot: Bot, chat_id: str):
    global _bot, _chat_id
    _bot = bot
    _chat_id = chat_id
    if chat_id:
        logger.info(f"[AdminNotify] Active → sending to {chat_id}")
    else:
        logger.info("[AdminNotify] Disabled — no ADMIN_GROUP_ID set")


async def _send(text: str):
    if not _bot or not _chat_id:
        return
    try:
        await _bot.send_message(
            chat_id=_chat_id, text=text, parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"[AdminNotify] Failed: {e}")


def _ts():
    return datetime.now().strftime("%d/%m/%Y • %H:%M:%S")


def _user_line(user):
    name = user.full_name or "—"
    uname = f"@{user.username}" if user.username else "No username"
    return name, uname


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🆕 NEW USER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def new_user(user):
    name, uname = _user_line(user)
    await _send(
        f"🆕 <b>New User Joined</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤  <b>{name}</b>\n"
        f"📎  {uname}\n"
        f"🆔  <code>{user.id}</code>\n\n"
        f"🕐  <code>{_ts()}</code>\n\n"
        f"#new_user"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🔄 USER RETURNED
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def user_started(user):
    name, uname = _user_line(user)
    await _send(
        f"🔄 <b>User Returned</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤  <b>{name}</b>  ·  {uname}\n"
        f"🆔  <code>{user.id}</code>\n"
        f"🕐  <code>{_ts()}</code>\n"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🛒 ORDER EVENTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def order_created(user, product_name: str, quantity: int, total: float):
    name, uname = _user_line(user)
    await _send(
        f"🛒 <b>New Order</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤  <b>{name}</b>  ·  {uname}\n"
        f"🆔  <code>{user.id}</code>\n\n"
        f"📦  <b>{product_name}</b>\n"
        f"🔢  Qty: <b>{quantity}</b>\n"
        f"💵  Total: <b>${total:.2f}</b>\n\n"
        f"🕐  <code>{_ts()}</code>\n\n"
        f"#order #pending"
    )


async def order_paid(user, product_name: str, total: float, method: str = "wallet"):
    name, uname = _user_line(user)
    icon = "👛" if method == "wallet" else "💳"
    await _send(
        f"✅ <b>Order Paid & Delivered</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤  <b>{name}</b>  ·  {uname}\n"
        f"🆔  <code>{user.id}</code>\n\n"
        f"📦  <b>{product_name}</b>\n"
        f"💰  <b>${total:.2f}</b>\n"
        f"{icon}  via <b>{method.upper()}</b>\n\n"
        f"🕐  <code>{_ts()}</code>\n\n"
        f"#sale #delivered ✅"
    )


async def order_cancelled(user_name: str, user_id, order_number: str, amount: float, reason: str = ""):
    reason_line = f"\n📝  Reason: <i>{reason}</i>" if reason else ""
    await _send(
        f"❌ <b>Order Cancelled</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤  <b>{user_name}</b>\n"
        f"🆔  <code>{user_id}</code>\n"
        f"🧾  <code>{order_number}</code>\n"
        f"💰  <b>${amount:.2f}</b>"
        f"{reason_line}\n\n"
        f"🕐  <code>{_ts()}</code>\n\n"
        f"#order #cancelled"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  💳 DEPOSIT EVENTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def deposit_request(user, amount: float, method: str, ref_id: str = ""):
    name, uname = _user_line(user)
    ref_line = f"\n🔖  Ref: <code>{ref_id}</code>" if ref_id else ""
    await _send(
        f"💳 <b>Deposit Request</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤  <b>{name}</b>  ·  {uname}\n"
        f"🆔  <code>{user.id}</code>\n\n"
        f"💵  Amount: <b>${amount:.2f}</b>\n"
        f"🏦  Method: <b>{method}</b>"
        f"{ref_line}\n\n"
        f"⏳  <i>Awaiting payment...</i>\n"
        f"🕐  <code>{_ts()}</code>\n\n"
        f"#deposit #pending"
    )


async def deposit_confirmed(user_name: str, user_id, amount: float, method: str, ref_id: str = "", new_balance: float = 0):
    ref_line = f"\n🔖  Ref: <code>{ref_id}</code>" if ref_id else ""
    await _send(
        f"✅ <b>Deposit Confirmed</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤  <b>{user_name}</b>\n"
        f"🆔  <code>{user_id}</code>\n\n"
        f"💰  <b>${amount:.2f}</b>  ·  {method}"
        f"{ref_line}\n"
        f"💎  New Balance: <b>${new_balance:.2f}</b>\n\n"
        f"🕐  <code>{_ts()}</code>\n\n"
        f"#deposit #confirmed ✅"
    )


async def deposit_rejected(user_name: str, user_id, amount: float, method: str, ref_id: str = ""):
    ref_line = f"\n🔖  Ref: <code>{ref_id}</code>" if ref_id else ""
    await _send(
        f"❌ <b>Deposit Rejected</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤  <b>{user_name}</b>\n"
        f"🆔  <code>{user_id}</code>\n\n"
        f"💵  <b>${amount:.2f}</b>  ·  {method}"
        f"{ref_line}\n\n"
        f"🕐  <code>{_ts()}</code>\n\n"
        f"#deposit #rejected"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🎫 SUPPORT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def support_ticket(user, message_text: str):
    name, uname = _user_line(user)
    preview = message_text[:200] + ("..." if len(message_text) > 200 else "")
    await _send(
        f"🎫 <b>Support Ticket</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤  <b>{name}</b>  ·  {uname}\n"
        f"🆔  <code>{user.id}</code>\n\n"
        f"💬  <i>{preview}</i>\n\n"
        f"🕐  <code>{_ts()}</code>\n\n"
        f"#support #ticket"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🔧 CUSTOM / GENERIC
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def custom(emoji: str, title: str, details: str):
    await _send(
        f"{emoji} <b>{title}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"{details}\n\n"
        f"🕐  <code>{_ts()}</code>"
    )
