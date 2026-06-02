"""Reply Keyboard Buttons API — manage bot keyboard buttons"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_admin
from models.cms import ReplyButton

router = APIRouter(prefix="/reply-buttons", tags=["reply-buttons"])


class ReplyButtonIn(BaseModel):
    key: str
    text_en: str
    text_ar: str
    emoji: str = "📌"
    action: str
    row_order: int = 0
    col_order: int = 0
    is_enabled: bool = True
    keyboard_type: str = "reply"


@router.get("")
async def list_reply_buttons(
    keyboard_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    query = select(ReplyButton).where(ReplyButton.is_deleted == False)
    if keyboard_type:
        query = query.where(ReplyButton.keyboard_type == keyboard_type)
    query = query.order_by(ReplyButton.keyboard_type, ReplyButton.row_order, ReplyButton.col_order)
    result = await db.execute(query)
    return {"buttons": [{
        "id": str(b.id), "key": b.key,
        "text_en": b.text_en, "text_ar": b.text_ar,
        "emoji": b.emoji, "action": b.action,
        "row_order": b.row_order, "col_order": b.col_order,
        "is_enabled": b.is_enabled,
        "keyboard_type": b.keyboard_type,
    } for b in result.scalars().all()]}


# Public endpoint for bot to fetch buttons (no admin auth)
@router.get("/public")
async def get_public_buttons(db: AsyncSession = Depends(get_db)):
    query = (
        select(ReplyButton)
        .where(ReplyButton.is_deleted == False, ReplyButton.is_enabled == True)
        .order_by(ReplyButton.keyboard_type, ReplyButton.row_order, ReplyButton.col_order)
    )
    result = await db.execute(query)
    buttons = result.scalars().all()
    reply_btns = []
    inline_btns = []
    for b in buttons:
        entry = {
            "key": b.key, "text_en": b.text_en, "text_ar": b.text_ar,
            "emoji": b.emoji, "action": b.action,
            "row_order": b.row_order, "col_order": b.col_order,
        }
        if b.keyboard_type == "reply":
            reply_btns.append(entry)
        else:
            inline_btns.append(entry)
    return {"reply": reply_btns, "inline": inline_btns}


@router.post("")
async def create_reply_button(data: ReplyButtonIn, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    existing = (await db.execute(
        select(ReplyButton).where(ReplyButton.key == data.key, ReplyButton.is_deleted == False)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(400, f"Button key '{data.key}' already exists")

    btn = ReplyButton(**data.model_dump())
    db.add(btn)
    await db.commit()
    return {"success": True, "id": str(btn.id)}


@router.put("/{btn_id}")
async def update_reply_button(btn_id: str, data: ReplyButtonIn, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    btn = (await db.execute(
        select(ReplyButton).where(ReplyButton.id == uuid.UUID(btn_id))
    )).scalar_one_or_none()
    if not btn:
        raise HTTPException(404, "Button not found")
    for k, v in data.model_dump().items():
        setattr(btn, k, v)
    await db.commit()
    return {"success": True}


@router.delete("/{btn_id}")
async def delete_reply_button(btn_id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    btn = (await db.execute(
        select(ReplyButton).where(ReplyButton.id == uuid.UUID(btn_id))
    )).scalar_one_or_none()
    if not btn:
        raise HTTPException(404, "Button not found")
    btn.is_deleted = True
    await db.commit()
    return {"success": True}
