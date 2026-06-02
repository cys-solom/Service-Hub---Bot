"""Backups API"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_admin
from models.system import Backup

router = APIRouter(prefix="/backups", tags=["backups"])

@router.get("")
async def list_backups(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(Backup).where(Backup.is_deleted == False).order_by(desc(Backup.created_at)))
    return {"backups": [{
        "id": str(b.id), "filename": b.filename, "size_bytes": b.size_bytes,
        "type": b.type, "status": b.status, "notes": b.notes,
        "created_at": b.created_at.isoformat(),
    } for b in result.scalars().all()]}

@router.post("/create")
async def create_backup(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    # Trigger backup task (placeholder — will be Celery task)
    import uuid
    from datetime import datetime, timezone
    backup = Backup(
        filename=f"backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.sql",
        size_bytes=0, type="full", status="queued", storage_path="/backups/",
        notes="Triggered from admin panel",
    )
    db.add(backup)
    await db.commit()
    return {"success": True, "id": str(backup.id), "message": "Backup queued"}


@router.delete("/{backup_id}")
async def delete_backup(backup_id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    import uuid as _uuid
    backup = (await db.execute(select(Backup).where(Backup.id == _uuid.UUID(backup_id)))).scalar_one_or_none()
    if not backup:
        from fastapi import HTTPException
        raise HTTPException(404, "Backup not found")
    await db.delete(backup)
    await db.commit()
    return {"success": True}
