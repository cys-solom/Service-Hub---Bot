"""Buttons Builder API"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_admin
from models.cms import ButtonTemplate

router = APIRouter(prefix="/buttons", tags=["buttons"])

class ButtonIn(BaseModel):
    name: str
    layout: dict  # JSON array of rows
    layout_i18n: Optional[dict] = None
    type: str = "inline"
    is_active: bool = True
    group: str = "general"

@router.get("")
async def list_buttons(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(ButtonTemplate).where(ButtonTemplate.is_deleted == False))
    return {"buttons": [{
        "id": str(b.id), "name": b.name, "layout": b.layout,
        "layout_i18n": b.layout_i18n, "type": b.type,
        "is_active": b.is_active, "group": b.group,
    } for b in result.scalars().all()]}

@router.post("")
async def create_button(data: ButtonIn, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    btn = ButtonTemplate(**data.model_dump())
    db.add(btn)
    await db.commit()
    return {"success": True, "id": str(btn.id)}

@router.put("/{btn_id}")
async def update_button(btn_id: str, data: ButtonIn, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    btn = (await db.execute(select(ButtonTemplate).where(ButtonTemplate.id == uuid.UUID(btn_id)))).scalar_one_or_none()
    if not btn: raise HTTPException(404, "Button template not found")
    for k, v in data.model_dump().items(): setattr(btn, k, v)
    await db.commit()
    return {"success": True}

@router.delete("/{btn_id}")
async def delete_button(btn_id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    btn = (await db.execute(select(ButtonTemplate).where(ButtonTemplate.id == uuid.UUID(btn_id)))).scalar_one_or_none()
    if not btn: raise HTTPException(404, "Not found")
    btn.is_deleted = True
    await db.commit()
    return {"success": True}
