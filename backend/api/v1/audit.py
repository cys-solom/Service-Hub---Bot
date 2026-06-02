"""Audit Logs API"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_admin
from models.system import AuditLog

router = APIRouter(prefix="/audit", tags=["audit"])

@router.get("")
async def list_logs(
    actor_type: str = "", action: str = "", page: int = 1, limit: int = 50,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    query = select(AuditLog)
    count_q = select(func.count(AuditLog.id))
    if actor_type:
        query = query.where(AuditLog.actor_type == actor_type)
        count_q = count_q.where(AuditLog.actor_type == actor_type)
    if action:
        query = query.where(AuditLog.action.ilike(f"%{action}%"))
        count_q = count_q.where(AuditLog.action.ilike(f"%{action}%"))
    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(query.order_by(desc(AuditLog.created_at)).offset((page-1)*limit).limit(limit))
    return {"logs": [{
        "id": str(l.id), "actor_type": l.actor_type, "actor_id": l.actor_id,
        "action": l.action, "resource_type": l.resource_type,
        "resource_id": l.resource_id, "details": l.details,
        "created_at": l.created_at.isoformat(),
    } for l in result.scalars().all()], "total": total, "page": page}
