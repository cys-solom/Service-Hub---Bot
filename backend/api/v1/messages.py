"""Messages Manager API"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_admin
from models.cms import MessageTemplate

router = APIRouter(prefix="/messages", tags=["messages"])

class MessageIn(BaseModel):
    key: str
    type: str = "text"
    content: str
    content_i18n: Optional[dict] = None
    media_url: Optional[str] = None
    parse_mode: str = "HTML"
    buttons_template_id: Optional[str] = None
    is_active: bool = True
    group: str = "general"

@router.get("")
async def list_messages(group: str = "", db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    query = select(MessageTemplate).where(MessageTemplate.is_deleted == False)
    if group: query = query.where(MessageTemplate.group == group)
    result = await db.execute(query.order_by(MessageTemplate.key))
    return {"messages": [{
        "id": str(m.id), "key": m.key, "type": m.type, "content": m.content,
        "content_i18n": m.content_i18n, "media_url": m.media_url,
        "parse_mode": m.parse_mode, "is_active": m.is_active, "group": m.group,
        "buttons_template_id": str(m.buttons_template_id) if m.buttons_template_id else None,
    } for m in result.scalars().all()]}

@router.post("")
async def create_message(data: MessageIn, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    msg = MessageTemplate(key=data.key, type=data.type, content=data.content,
        content_i18n=data.content_i18n, media_url=data.media_url, parse_mode=data.parse_mode,
        buttons_template_id=uuid.UUID(data.buttons_template_id) if data.buttons_template_id else None,
        is_active=data.is_active, group=data.group)
    db.add(msg)
    await db.commit()
    return {"success": True, "id": str(msg.id)}

@router.put("/{msg_id}")
async def update_message(msg_id: str, data: MessageIn, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    msg = (await db.execute(select(MessageTemplate).where(MessageTemplate.id == uuid.UUID(msg_id)))).scalar_one_or_none()
    if not msg: raise HTTPException(404, "Message not found")
    for k, v in data.model_dump().items():
        if k == "buttons_template_id" and v: v = uuid.UUID(v)
        setattr(msg, k, v)
    await db.commit()
    return {"success": True}

@router.delete("/{msg_id}")
async def delete_message(msg_id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    msg = (await db.execute(select(MessageTemplate).where(MessageTemplate.id == uuid.UUID(msg_id)))).scalar_one_or_none()
    if not msg: raise HTTPException(404, "Message not found")
    msg.is_deleted = True
    await db.commit()
    return {"success": True}
