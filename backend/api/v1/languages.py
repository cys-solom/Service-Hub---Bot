"""Languages API"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_admin
from models.system import Language, Translation

router = APIRouter(prefix="/languages", tags=["languages"])

@router.get("")
async def list_languages(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Language).where(Language.is_deleted == False).order_by(Language.name))
    return {"languages": [{
        "id": str(l.id), "code": l.code, "name": l.name,
        "native_name": l.native_name, "is_rtl": l.is_rtl,
        "is_default": l.is_default, "is_enabled": l.is_enabled,
        "flag_emoji": l.flag_emoji,
    } for l in result.scalars().all()]}

@router.get("/translations/{lang_code}")
async def get_translations(lang_code: str, group: str = "", db: AsyncSession = Depends(get_db)):
    query = select(Translation).where(Translation.language_code == lang_code, Translation.is_deleted == False)
    if group: query = query.where(Translation.group == group)
    result = await db.execute(query)
    return {"translations": {t.key: t.value for t in result.scalars().all()}}

class TranslationBulk(BaseModel):
    translations: dict  # {"key": "value", ...}
    group: str = "bot"

@router.put("/translations/{lang_code}")
async def save_translations(lang_code: str, data: TranslationBulk,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    for key, value in data.translations.items():
        existing = (await db.execute(
            select(Translation).where(Translation.language_code == lang_code, Translation.key == key)
        )).scalar_one_or_none()
        if existing:
            existing.value = value
        else:
            db.add(Translation(language_code=lang_code, key=key, value=value, group=data.group))
    await db.commit()
    return {"success": True}
