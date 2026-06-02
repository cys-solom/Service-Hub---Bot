"""Support Tickets API — with Telegram notifications"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_admin
from core.telegram import send_telegram
from models.support import SupportTicket
from models.user import User

router = APIRouter(prefix="/support", tags=["support"])
logger = logging.getLogger(__name__)


@router.get("")
async def list_tickets(status: str = "", page: int = 1, limit: int = 20,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    query = select(SupportTicket, User).join(User, SupportTicket.user_id == User.id).where(SupportTicket.is_deleted == False)
    count_q = select(func.count(SupportTicket.id)).where(SupportTicket.is_deleted == False)
    if status:
        query = query.where(SupportTicket.status == status)
        count_q = count_q.where(SupportTicket.status == status)
    total = (await db.execute(count_q)).scalar() or 0

    # Count by status for tabs
    open_count = (await db.execute(
        select(func.count(SupportTicket.id)).where(SupportTicket.is_deleted == False, SupportTicket.status == "open")
    )).scalar() or 0
    progress_count = (await db.execute(
        select(func.count(SupportTicket.id)).where(SupportTicket.is_deleted == False, SupportTicket.status == "in_progress")
    )).scalar() or 0

    result = await db.execute(query.order_by(desc(SupportTicket.created_at)).offset((page-1)*limit).limit(limit))
    return {
        "tickets": [{
            "id": str(t.id), "user_id": str(t.user_id),
            "user": u.username or f"ID:{u.telegram_id}",
            "telegram_id": u.telegram_id,
            "display_name": " ".join(filter(None, [u.first_name, u.last_name])) or u.username or f"ID:{u.telegram_id}",
            "subject": t.subject, "message": t.message, "status": t.status,
            "priority": t.priority, "replies": t.replies or [],
            "order_id": str(t.order_id) if t.order_id else None,
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat() if t.updated_at else t.created_at.isoformat(),
        } for t, u in result.all()],
        "total": total, "page": page,
        "pages": max(1, (total + limit - 1) // limit),
        "open_count": open_count, "in_progress_count": progress_count,
    }


@router.get("/stats")
async def ticket_stats(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    total = (await db.execute(select(func.count(SupportTicket.id)).where(SupportTicket.is_deleted == False))).scalar() or 0
    open_c = (await db.execute(
        select(func.count(SupportTicket.id)).where(SupportTicket.is_deleted == False, SupportTicket.status == "open")
    )).scalar() or 0
    in_progress = (await db.execute(
        select(func.count(SupportTicket.id)).where(SupportTicket.is_deleted == False, SupportTicket.status == "in_progress")
    )).scalar() or 0
    resolved = (await db.execute(
        select(func.count(SupportTicket.id)).where(SupportTicket.is_deleted == False, SupportTicket.status == "resolved")
    )).scalar() or 0
    return {"total": total, "open": open_c, "in_progress": in_progress, "resolved": resolved}


class TicketReply(BaseModel):
    message: str


@router.post("/{ticket_id}/reply")
async def reply_ticket(ticket_id: str, data: TicketReply,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    ticket = (await db.execute(select(SupportTicket).where(SupportTicket.id == uuid.UUID(ticket_id)))).scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    replies = list(ticket.replies or [])
    replies.append({
        "sender": "admin", "message": data.message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    ticket.replies = replies
    if ticket.status == "open":
        ticket.status = "in_progress"
    await db.commit()

    # 🔔 Send notification to user via Telegram
    user = (await db.execute(select(User).where(User.id == ticket.user_id))).scalar_one_or_none()
    if user and user.telegram_id:
        text = (
            f"💬 <b>New Reply on Your Ticket</b>\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"📋 <b>{ticket.subject}</b>\n\n"
            f"👨‍💼 <b>Admin:</b>\n"
            f"{data.message}\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"Use /support to view your tickets."
        )
        sent = await send_telegram(user.telegram_id, text)
        logger.info(f"[Support] Reply notification sent to {user.telegram_id}: {sent}")

    return {"success": True, "replies": replies}


class TicketStatusUpdate(BaseModel):
    status: str


@router.put("/{ticket_id}/status")
async def update_ticket_status(ticket_id: str, data: TicketStatusUpdate,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    ticket = (await db.execute(select(SupportTicket).where(SupportTicket.id == uuid.UUID(ticket_id)))).scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    ticket.status = data.status
    await db.commit()

    # Notify user of status change
    user = (await db.execute(select(User).where(User.id == ticket.user_id))).scalar_one_or_none()
    if user and user.telegram_id:
        status_emoji = {"resolved": "✅", "closed": "🔒", "in_progress": "⏳", "open": "📬"}.get(data.status, "📌")
        text = (
            f"{status_emoji} <b>Ticket Update</b>\n\n"
            f"📋 <b>{ticket.subject}</b>\n"
            f"Status: <b>{data.status.replace('_', ' ').title()}</b>"
        )
        await send_telegram(user.telegram_id, text)

    return {"success": True}


class TicketPriorityUpdate(BaseModel):
    priority: str


@router.put("/{ticket_id}/priority")
async def update_ticket_priority(ticket_id: str, data: TicketPriorityUpdate,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    ticket = (await db.execute(select(SupportTicket).where(SupportTicket.id == uuid.UUID(ticket_id)))).scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    ticket.priority = data.priority
    await db.commit()
    return {"success": True}


@router.delete("/{ticket_id}")
async def delete_ticket(ticket_id: str,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    ticket = (await db.execute(select(SupportTicket).where(SupportTicket.id == uuid.UUID(ticket_id)))).scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    ticket.is_deleted = True
    await db.commit()
    return {"success": True}
