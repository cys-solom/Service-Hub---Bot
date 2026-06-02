"""Crypto Verification API — on-chain payment checking"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_admin
from models.payment import Payment, PaymentMethod

router = APIRouter(prefix="/crypto", tags=["crypto"])


class CryptoCheckRequest(BaseModel):
    wallet_address: str
    expected_amount: float
    network: str  # trc20, bep20, btc


class CryptoCheckResponse(BaseModel):
    found: bool
    tx_hash: Optional[str] = None
    amount: Optional[float] = None
    confirmations: Optional[int] = None


@router.post("/check", response_model=CryptoCheckResponse)
async def check_crypto_payment(data: CryptoCheckRequest, admin=Depends(get_current_admin)):
    """Manually check if a crypto payment was received"""
    import httpx

    try:
        if data.network == "trc20":
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"https://api.trongrid.io/v1/accounts/{data.wallet_address}/transactions/trc20",
                    params={"limit": 30, "only_confirmed": "true"},
                )
                if resp.status_code == 200:
                    txns = resp.json().get("data", [])
                    for tx in txns:
                        value = int(tx.get("value", 0)) / 1_000_000
                        if abs(value - data.expected_amount) < 0.02:
                            return CryptoCheckResponse(
                                found=True,
                                tx_hash=tx.get("transaction_id"),
                                amount=value,
                                confirmations=1,
                            )

        elif data.network == "bep20":
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://api.bscscan.com/api",
                    params={
                        "module": "account", "action": "tokentx",
                        "address": data.wallet_address,
                        "sort": "desc", "page": 1, "offset": 30,
                    },
                )
                if resp.status_code == 200:
                    txns = resp.json().get("result", [])
                    for tx in txns:
                        decimals = int(tx.get("tokenDecimal", 18))
                        value = int(tx.get("value", 0)) / (10 ** decimals)
                        if abs(value - data.expected_amount) < 0.02:
                            return CryptoCheckResponse(
                                found=True,
                                tx_hash=tx.get("hash"),
                                amount=value,
                                confirmations=int(tx.get("confirmations", 0)),
                            )

        elif data.network == "btc":
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"https://blockchain.info/rawaddr/{data.wallet_address}",
                    params={"limit": 15},
                )
                if resp.status_code == 200:
                    txns = resp.json().get("txs", [])
                    for tx in txns:
                        for out in tx.get("out", []):
                            if out.get("addr") == data.wallet_address:
                                value_btc = out.get("value", 0) / 100_000_000
                                return CryptoCheckResponse(
                                    found=True,
                                    tx_hash=tx.get("hash"),
                                    amount=value_btc,
                                )

    except Exception as e:
        raise HTTPException(500, f"Verification error: {str(e)}")

    return CryptoCheckResponse(found=False)


@router.post("/verify-payment/{payment_id}")
async def verify_and_confirm(
    payment_id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    """Trigger on-chain verification for a specific payment"""
    payment = (await db.execute(
        select(Payment).where(Payment.id == uuid.UUID(payment_id))
    )).scalar_one_or_none()
    if not payment:
        raise HTTPException(404, "Payment not found")

    method = (await db.execute(
        select(PaymentMethod).where(PaymentMethod.code == payment.method_code)
    )).scalar_one_or_none()

    if not method or not method.wallet_address:
        raise HTTPException(400, "No wallet address configured for this method")

    # Determine network
    network = "trc20"
    if "bep20" in payment.method_code:
        network = "bep20"
    elif "btc" in payment.method_code:
        network = "btc"

    # Check on-chain
    result = await check_crypto_payment(
        CryptoCheckRequest(
            wallet_address=method.wallet_address,
            expected_amount=float(payment.amount),
            network=network,
        ),
        admin=admin,
    )

    if result.found:
        payment.status = "confirmed"
        payment.tx_hash = result.tx_hash

        # Update order
        from models.order import Order
        order = (await db.execute(select(Order).where(Order.id == payment.order_id))).scalar_one_or_none()
        if order:
            order.status = "paid"
        await db.commit()

        return {"verified": True, "tx_hash": result.tx_hash, "amount": result.amount}

    return {"verified": False, "message": "Payment not found on-chain yet"}
