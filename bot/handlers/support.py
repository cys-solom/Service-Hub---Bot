"""Support handler — create, view, and reply to support tickets"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
from models.user import User
from models.support import SupportTicket

from config import settings
from bot_services.store_settings import get_setting
from bot_services import admin_notify

router = Router()


class SupportForm(StatesGroup):
    subject = State()
    message = State()


class TicketReplyForm(StatesGroup):
    waiting_reply = State()


def _sid(uid):
    return str(uid).replace('-', '')

def _eid(short):
    h = short.strip()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def _support_menu_kb(lang="en"):
    builder = InlineKeyboardBuilder()
    if lang == "ar":
        builder.row(InlineKeyboardButton(text="📝 تذكرة جديدة", callback_data="support:new"))
        builder.row(InlineKeyboardButton(text="📋 تذاكري", callback_data="support:list"))
    else:
        builder.row(InlineKeyboardButton(text="📝 New Ticket", callback_data="support:new"))
        builder.row(InlineKeyboardButton(text="📋 My Tickets", callback_data="support:list"))
    builder.row(InlineKeyboardButton(text="⬅️ Back", callback_data="menu:back"))
    return builder.as_markup()


@router.message(Command("support"))
@router.callback_query(F.data == "menu:support")
async def support_menu(event, state: FSMContext, session: AsyncSession, lang: str = "en"):
    """Go directly to ticket creation — simpler flow"""
    await state.clear()

    user = (await session.execute(
        select(User).where(User.telegram_id == event.from_user.id)
    )).scalar_one_or_none()

    # Check if they have existing tickets with replies
    has_tickets = False
    if user:
        has_tickets = bool((await session.execute(
            select(func.count(SupportTicket.id)).where(
                SupportTicket.user_id == user.id,
                SupportTicket.is_deleted == False,
            )
        )).scalar())

    if lang == "ar":
        text = (
            "🆘 <b>الدعم الفني — تذكرة جديدة</b>\n"
            "━━━━━━━━━━━━━━━\n\n"
            "📝 أرسل <b>موضوع</b> المشكلة:"
        )
    else:
        text = (
            "🆘 <b>Support — New Ticket</b>\n"
            "━━━━━━━━━━━━━━━\n\n"
            "📝 Send the <b>subject</b> of your issue:"
        )

    builder = InlineKeyboardBuilder()
    if has_tickets:
        builder.row(InlineKeyboardButton(
            text="📋 My Tickets" if lang == "en" else "📋 تذاكري",
            callback_data="support:list",
        ))
    builder.row(InlineKeyboardButton(text="⬅️ Back", callback_data="menu:back"))

    msg = event if isinstance(event, Message) else event.message
    try:
        if isinstance(event, CallbackQuery):
            await msg.edit_text(text, reply_markup=builder.as_markup())
            await event.answer()
        else:
            await msg.answer(text, reply_markup=builder.as_markup())
    except Exception:
        await msg.answer(text, reply_markup=builder.as_markup())

    await state.set_state(SupportForm.subject)


# ─── NEW TICKET ──────────────────────────────────────
@router.callback_query(F.data == "support:new")
async def new_ticket(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    text = "📝 Send the <b>subject</b> of your issue:" if lang == "en" \
        else "📝 أرسل <b>موضوع</b> المشكلة:"
    await callback.message.edit_text(text)
    await state.set_state(SupportForm.subject)
    await callback.answer()


@router.message(SupportForm.subject)
async def get_subject(message: Message, state: FSMContext, lang: str = "en"):
    await state.update_data(subject=message.text)
    text = "Now <b>describe</b> your issue in detail:" if lang == "en" \
        else "الآن <b>اشرح</b> مشكلتك بالتفصيل:"
    await message.answer(text)
    await state.set_state(SupportForm.message)


@router.message(SupportForm.message)
async def submit_ticket(message: Message, state: FSMContext, session: AsyncSession, lang: str = "en"):
    data = await state.get_data()
    await state.clear()

    user = (await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )).scalar_one_or_none()

    if not user:
        from models.user import User as UserModel
        user = UserModel(telegram_id=message.from_user.id, first_name=message.from_user.first_name or "User")
        session.add(user)
        await session.flush()

    ticket = SupportTicket(
        user_id=user.id,
        subject=data["subject"],
        message=message.text,
        status="open",
        priority="normal",
        replies=[{"sender": "user", "message": message.text, "timestamp": datetime.now(timezone.utc).isoformat()}],
    )
    session.add(ticket)
    await session.commit()

    # ── Admin notify ──
    await admin_notify.support_ticket(message.from_user, f"[{data['subject']}] {message.text}")

    ticket_num = str(ticket.id)[:8].upper()

    if lang == "ar":
        text = (
            f"✅ <b>تم إرسال التذكرة بنجاح!</b>\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"🎫 التذكرة: <code>{ticket_num}</code>\n"
            f"📋 الموضوع: {data['subject']}\n\n"
            f"سيتم الرد عليك في أقرب وقت.\n"
            f"ستصلك رسالة هنا عند الرد! 🔔"
        )
    else:
        text = (
            f"✅ <b>Ticket Submitted!</b>\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"🎫 Ticket: <code>{ticket_num}</code>\n"
            f"📋 Subject: {data['subject']}\n\n"
            f"We'll get back to you shortly.\n"
            f"You'll receive a message here when we reply! 🔔"
        )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="📋 My Tickets" if lang == "en" else "📋 تذاكري",
        callback_data="support:list",
    ))
    builder.row(InlineKeyboardButton(text="⬅️ Back", callback_data="menu:back"))
    await message.answer(text, reply_markup=builder.as_markup())


# ─── LIST TICKETS ────────────────────────────────────
@router.callback_query(F.data == "support:list")
async def list_tickets(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str = "en"):
    await state.clear()
    user = (await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )).scalar_one_or_none()

    if not user:
        await callback.answer("No tickets found" if lang == "en" else "لا توجد تذاكر", show_alert=True)
        return

    tickets = (await session.execute(
        select(SupportTicket)
        .where(SupportTicket.user_id == user.id, SupportTicket.is_deleted == False)
        .order_by(desc(SupportTicket.created_at))
        .limit(10)
    )).scalars().all()

    if not tickets:
        await callback.answer("No tickets yet" if lang == "en" else "لا توجد تذاكر بعد", show_alert=True)
        return

    status_emoji = {"open": "📬", "in_progress": "⏳", "resolved": "✅", "closed": "🔒"}

    if lang == "ar":
        text = "📋 <b>تذاكري</b>\n━━━━━━━━━━━━━━━\n\n"
    else:
        text = "📋 <b>My Tickets</b>\n━━━━━━━━━━━━━━━\n\n"

    builder = InlineKeyboardBuilder()
    for t in tickets:
        emoji = status_emoji.get(t.status, "📌")
        replies_count = len(t.replies or [])
        has_new = any(r.get("sender") == "admin" for r in (t.replies or [])[-3:])
        new_badge = " 🔴" if has_new and t.status != "closed" else ""

        label = f"{emoji} {t.subject[:30]}{new_badge}"
        builder.row(InlineKeyboardButton(
            text=label,
            callback_data=f"ticket:{_sid(t.id)}",
        ))

    builder.row(InlineKeyboardButton(
        text="📝 New Ticket" if lang == "en" else "📝 تذكرة جديدة",
        callback_data="support:new",
    ))
    builder.row(InlineKeyboardButton(text="⬅️ Back", callback_data="menu:support"))

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except Exception:
        await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


# ─── VIEW TICKET ─────────────────────────────────────
@router.callback_query(F.data.startswith("ticket:"))
async def view_ticket(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str = "en"):
    await state.clear()
    tid = callback.data.split(":")[1]
    ticket_id = _eid(tid)

    ticket = (await session.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )).scalar_one_or_none()

    if not ticket:
        await callback.answer("Ticket not found", show_alert=True)
        return

    status_emoji = {"open": "📬", "in_progress": "⏳", "resolved": "✅", "closed": "🔒"}
    emoji = status_emoji.get(ticket.status, "📌")

    # Build conversation view
    text = (
        f"🎫 <b>Ticket</b> — {emoji} {ticket.status.replace('_', ' ').title()}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📋 <b>{ticket.subject}</b>\n\n"
    )

    replies = ticket.replies or []
    # Show last 8 messages to avoid hitting Telegram's message limit
    display_replies = replies[-8:]
    if len(replies) > 8:
        text += f"<i>... {len(replies) - 8} earlier messages</i>\n\n"

    for r in display_replies:
        sender = r.get("sender", "user")
        msg = r.get("message", "")
        ts = r.get("timestamp", "")
        time_str = ""
        if ts:
            try:
                dt = datetime.fromisoformat(ts)
                time_str = dt.strftime("%m/%d %H:%M")
            except Exception:
                pass

        if sender == "admin":
            text += f"👨‍💼 <b>Admin</b> <i>{time_str}</i>\n{msg}\n\n"
        else:
            text += f"👤 <b>You</b> <i>{time_str}</i>\n{msg}\n\n"

    text += "━━━━━━━━━━━━━━━"

    builder = InlineKeyboardBuilder()
    if ticket.status not in ("closed", "resolved"):
        builder.row(InlineKeyboardButton(
            text="💬 Reply" if lang == "en" else "💬 رد",
            callback_data=f"ticket_reply:{tid}",
        ))
        builder.row(InlineKeyboardButton(
            text="🔒 Close Ticket" if lang == "en" else "🔒 إغلاق التذكرة",
            callback_data=f"ticket_close:{tid}",
        ))
    builder.row(InlineKeyboardButton(
        text="⬅️ Back" if lang == "en" else "⬅️ رجوع",
        callback_data="support:list",
    ))

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except Exception:
        await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


# ─── REPLY TO TICKET ─────────────────────────────────
@router.callback_query(F.data.startswith("ticket_reply:"))
async def start_reply(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    tid = callback.data.split(":")[1]
    await state.set_state(TicketReplyForm.waiting_reply)
    await state.update_data(ticket_sid=tid)

    text = "💬 Type your reply:" if lang == "en" else "💬 اكتب ردك:"
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="❌ Cancel" if lang == "en" else "❌ إلغاء",
        callback_data=f"ticket:{tid}",
    ))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.message(TicketReplyForm.waiting_reply)
async def recv_reply(message: Message, state: FSMContext, session: AsyncSession, lang: str = "en"):
    data = await state.get_data()
    tid = data.get("ticket_sid")
    await state.clear()

    ticket_id = _eid(tid)
    ticket = (await session.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )).scalar_one_or_none()

    if not ticket:
        await message.answer("Ticket not found.")
        return

    replies = list(ticket.replies or [])
    replies.append({
        "sender": "user",
        "message": message.text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    ticket.replies = replies
    if ticket.status in ("resolved", "closed"):
        ticket.status = "open"  # Reopen if user replies
    await session.commit()

    text = "✅ Reply sent!" if lang == "en" else "✅ تم إرسال الرد!"
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="📋 View Ticket" if lang == "en" else "📋 عرض التذكرة",
        callback_data=f"ticket:{tid}",
    ))
    builder.row(InlineKeyboardButton(text="⬅️ Back", callback_data="support:list"))
    await message.answer(text, reply_markup=builder.as_markup())


# ─── CLOSE TICKET ────────────────────────────────────
@router.callback_query(F.data.startswith("ticket_close:"))
async def close_ticket(callback: CallbackQuery, session: AsyncSession, lang: str = "en"):
    tid = callback.data.split(":")[1]
    ticket_id = _eid(tid)

    ticket = (await session.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )).scalar_one_or_none()

    if ticket:
        ticket.status = "closed"
        await session.commit()

    text = "🔒 Ticket closed." if lang == "en" else "🔒 تم إغلاق التذكرة."
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📋 My Tickets", callback_data="support:list"))
    builder.row(InlineKeyboardButton(text="⬅️ Back", callback_data="menu:back"))

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except Exception:
        await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()
