"""Wallets API"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_admin
from models.wallet import Wallet, WalletTransaction

router = APIRouter(prefix="/wallets", tags=["wallets"])

@router.get("/{user_id}")
async def get_wallet(user_id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    wallet = (await db.execute(select(Wallet).where(Wallet.user_id == uuid.UUID(user_id)))).scalar_one_or_none()
    if not wallet:
        return {"balance": 0, "total_deposited": 0, "total_spent": 0, "transactions": []}
    txns = await db.execute(
        select(WalletTransaction).where(WalletTransaction.wallet_id == wallet.id)
        .order_by(desc(WalletTransaction.created_at)).limit(50)
    )
    return {
        "balance": round(wallet.balance, 2),
        "total_deposited": round(wallet.total_deposited, 2),
        "total_spent": round(wallet.total_spent, 2),
        "transactions": [{
            "id": str(t.id), "type": t.type, "amount": t.amount,
            "balance_after": t.balance_after, "description": t.description,
            "created_at": t.created_at.isoformat(),
        } for t in txns.scalars().all()],
    }
