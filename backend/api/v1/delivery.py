"""Delivery Rules API"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_admin
from models.delivery import DeliveryRule

router = APIRouter(prefix="/delivery", tags=["delivery"])

class DeliveryRuleIn(BaseModel):
    name: str
    mode: str = "auto"
    description: Optional[str] = None
    template: Optional[str] = None
    template_i18n: Optional[dict] = None
    is_default: bool = False
    config: Optional[dict] = None

@router.get("")
async def list_rules(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(DeliveryRule).where(DeliveryRule.is_deleted == False).order_by(DeliveryRule.sort_order))
    return {"rules": [{
        "id": str(r.id), "name": r.name, "mode": r.mode,
        "description": r.description, "template": r.template,
        "is_default": r.is_default, "config": r.config,
    } for r in result.scalars().all()]}

@router.post("")
async def create_rule(data: DeliveryRuleIn, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    rule = DeliveryRule(**data.model_dump())
    db.add(rule)
    await db.commit()
    return {"success": True, "id": str(rule.id)}

@router.put("/{rule_id}")
async def update_rule(rule_id: str, data: DeliveryRuleIn, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    rule = (await db.execute(select(DeliveryRule).where(DeliveryRule.id == uuid.UUID(rule_id)))).scalar_one_or_none()
    if not rule: raise HTTPException(404, "Not found")
    for k, v in data.model_dump().items(): setattr(rule, k, v)
    await db.commit()
    return {"success": True}
