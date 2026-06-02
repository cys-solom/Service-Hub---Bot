"""External Providers API"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_admin
from models.provider import ExternalProvider, ProviderProduct

router = APIRouter(prefix="/providers", tags=["providers"])

class ProviderIn(BaseModel):
    name: str
    code: str
    api_url: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    is_enabled: bool = True
    config: Optional[dict] = None
    description: Optional[str] = None

@router.get("")
async def list_providers(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(ExternalProvider).where(ExternalProvider.is_deleted == False))
    return {"providers": [{
        "id": str(p.id), "name": p.name, "code": p.code,
        "api_url": p.api_url, "is_enabled": p.is_enabled,
        "config": p.config, "description": p.description,
        "last_sync_at": p.last_sync_at,
    } for p in result.scalars().all()]}

@router.post("")
async def create_provider(data: ProviderIn, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    provider = ExternalProvider(**data.model_dump())
    db.add(provider)
    await db.commit()
    return {"success": True, "id": str(provider.id)}

@router.put("/{provider_id}")
async def update_provider(provider_id: str, data: ProviderIn, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    p = (await db.execute(select(ExternalProvider).where(ExternalProvider.id == uuid.UUID(provider_id)))).scalar_one_or_none()
    if not p: raise HTTPException(404, "Provider not found")
    for k, v in data.model_dump().items(): setattr(p, k, v)
    await db.commit()
    return {"success": True}

@router.get("/{provider_id}/products")
async def list_provider_products(provider_id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(
        select(ProviderProduct).where(ProviderProduct.provider_id == uuid.UUID(provider_id), ProviderProduct.is_deleted == False)
    )
    return {"products": [{
        "id": str(pp.id), "external_code": pp.external_code, "name": pp.name,
        "cost_price": pp.cost_price, "is_available": pp.is_available,
        "product_id": str(pp.product_id) if pp.product_id else None,
    } for pp in result.scalars().all()]}
