"""Notifications API"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_admin
from models.system import Notification, NotificationLog

router = APIRouter(prefix="/notifications", tags=["notifications"])

class NotificationIn(BaseModel):
    type: str
    target: str
    channel: str = "telegram"
    template: str
    is_enabled: bool = True
    config: Optional[dict] = None

@router.get("")
async def list_notifications(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(Notification).where(Notification.is_deleted == False))
    return {"notifications": [{
        "id": str(n.id), "type": n.type, "target": n.target,
        "channel": n.channel, "template": n.template,
        "is_enabled": n.is_enabled, "config": n.config,
    } for n in result.scalars().all()]}

@router.post("")
async def create_notification(data: NotificationIn, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    n = Notification(**data.model_dump())
    db.add(n)
    await db.commit()
    return {"success": True, "id": str(n.id)}

@router.put("/{notif_id}")
async def update_notification(notif_id: str, data: NotificationIn, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    n = (await db.execute(select(Notification).where(Notification.id == uuid.UUID(notif_id)))).scalar_one_or_none()
    if not n: raise HTTPException(404, "Not found")
    for k, v in data.model_dump().items(): setattr(n, k, v)
    await db.commit()
    return {"success": True}

@router.get("/logs")
async def list_notification_logs(page: int = 1, limit: int = 50, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(NotificationLog).order_by(desc(NotificationLog.created_at)).offset((page-1)*limit).limit(limit))
    return {"logs": [{
        "id": str(l.id), "channel": l.channel, "recipient_id": l.recipient_id,
        "status": l.status, "error": l.error, "created_at": l.created_at.isoformat(),
    } for l in result.scalars().all()]}
