"""Commands Manager API — with admin/user categorization"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_admin
from models.cms import CommandTemplate

router = APIRouter(prefix="/commands", tags=["commands"])


class CommandIn(BaseModel):
    command: str
    description: Optional[str] = None
    is_enabled: bool = True
    is_admin: bool = False
    category: str = "general"
    response_message_id: Optional[str] = None
    cooldown_seconds: int = 0
    sort_order: int = 0


@router.get("")
async def list_commands(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    query = select(CommandTemplate).where(CommandTemplate.is_deleted == False)
    if category:
        query = query.where(CommandTemplate.category == category)
    query = query.order_by(CommandTemplate.sort_order, CommandTemplate.command)
    result = await db.execute(query)
    return {"commands": [{
        "id": str(c.id), "command": c.command, "description": c.description,
        "is_enabled": c.is_enabled, "is_admin": c.is_admin, "category": c.category,
        "response_message_id": str(c.response_message_id) if c.response_message_id else None,
        "cooldown_seconds": c.cooldown_seconds, "sort_order": c.sort_order,
    } for c in result.scalars().all()]}


@router.post("")
async def create_command(data: CommandIn, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    # Check for duplicate
    existing = (await db.execute(
        select(CommandTemplate).where(CommandTemplate.command == data.command, CommandTemplate.is_deleted == False)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(400, f"Command /{data.command} already exists")

    cmd = CommandTemplate(
        command=data.command, description=data.description, is_enabled=data.is_enabled,
        is_admin=data.is_admin, category=data.category,
        response_message_id=uuid.UUID(data.response_message_id) if data.response_message_id else None,
        cooldown_seconds=data.cooldown_seconds, sort_order=data.sort_order,
    )
    db.add(cmd)
    await db.commit()
    return {"success": True, "id": str(cmd.id)}


@router.put("/{cmd_id}")
async def update_command(cmd_id: str, data: CommandIn, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    cmd = (await db.execute(select(CommandTemplate).where(CommandTemplate.id == uuid.UUID(cmd_id)))).scalar_one_or_none()
    if not cmd:
        raise HTTPException(404, "Command not found")
    cmd.command = data.command
    cmd.description = data.description
    cmd.is_enabled = data.is_enabled
    cmd.is_admin = data.is_admin
    cmd.category = data.category
    cmd.cooldown_seconds = data.cooldown_seconds
    cmd.sort_order = data.sort_order
    if data.response_message_id:
        cmd.response_message_id = uuid.UUID(data.response_message_id)
    await db.commit()
    return {"success": True}


@router.delete("/{cmd_id}")
async def delete_command(cmd_id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    cmd = (await db.execute(select(CommandTemplate).where(CommandTemplate.id == uuid.UUID(cmd_id)))).scalar_one_or_none()
    if not cmd:
        raise HTTPException(404, "Command not found")
    cmd.is_deleted = True
    await db.commit()
    return {"success": True}
