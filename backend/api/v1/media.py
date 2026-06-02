"""Media Files API"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_admin
from models.system import MediaFile

router = APIRouter(prefix="/media", tags=["media"])

@router.get("")
async def list_media(group: str = "", page: int = 1, limit: int = 50,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    query = select(MediaFile).where(MediaFile.is_deleted == False)
    if group: query = query.where(MediaFile.group == group)
    result = await db.execute(query.order_by(desc(MediaFile.created_at)).offset((page-1)*limit).limit(limit))
    return {"files": [{
        "id": str(f.id), "filename": f.filename, "original_name": f.original_name,
        "mime_type": f.mime_type, "size_bytes": f.size_bytes,
        "url": f.url, "group": f.group, "created_at": f.created_at.isoformat(),
    } for f in result.scalars().all()]}
