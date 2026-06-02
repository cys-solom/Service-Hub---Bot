"""Payment tasks — expire old payments, verify crypto on-chain"""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

from workers.celery_app import app

logger = logging.getLogger(__name__)

# Sync engine for Celery (Celery doesn't support async natively)
from core.config import settings
SYNC_DB_URL = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2").replace("postgresql+psycopg2", "postgresql")
engine = create_engine(SYNC_DB_URL, pool_size=5)


@app.task(name="workers.tasks.payment_tasks.check_expired_payments")
def check_expired_payments():
    """Cancel orders with expired payment windows"""
    from models.order import Order
    from models.stock import StockItem
    from models.payment import Payment

    timeout = settings.PAYMENT_TIMEOUT_MINUTES if hasattr(settings, 'PAYMENT_TIMEOUT_MINUTES') else 30
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout)

    with Session(engine) as session:
        expired_orders = session.execute(
            select(Order).where(
                Order.status.in_(["waiting_payment", "pending"]),
                Order.created_at < cutoff,
            )
        ).scalars().all()

        canceled = 0
        for order in expired_orders:
            order.status = "canceled"

            # Unreserve stock
            items = session.execute(
                select(StockItem).where(StockItem.order_id == order.id, StockItem.is_reserved == True)
            ).scalars().all()
            for item in items:
                item.is_reserved = False
                item.order_id = None

            # Update payment status
            payments = session.execute(
                select(Payment).where(Payment.order_id == order.id, Payment.status == "pending")
            ).scalars().all()
            for p in payments:
                p.status = "expired"

            canceled += 1

        session.commit()
        logger.info(f"Expired {canceled} orders")
        return {"canceled": canceled}


@app.task(name="workers.tasks.payment_tasks.verify_crypto_payment")
def verify_crypto_payment(payment_id: str, method_code: str):
    """Verify a crypto payment on-chain"""
    from models.payment import Payment, PaymentMethod
    from models.order import Order
    from models.user import User
    from models.wallet import Wallet, WalletTransaction
    import uuid

    with Session(engine) as session:
        payment = session.execute(
            select(Payment).where(Payment.id == uuid.UUID(payment_id))
        ).scalar_one_or_none()

        if not payment or payment.status != "pending":
            return {"status": "skipped", "reason": "Not pending"}

        method = session.execute(
            select(PaymentMethod).where(PaymentMethod.code == method_code)
        ).scalar_one_or_none()

        if not method:
            return {"status": "error", "reason": "Method not found"}

        # Check on-chain based on method type
        verified = False
        if "trc20" in method_code or "bep20" in method_code:
            verified = _check_tron_or_bsc(payment, method)
        elif "btc" in method_code:
            verified = _check_btc(payment, method)

        if verified:
            payment.status = "confirmed"
            order = session.execute(
                select(Order).where(Order.id == payment.order_id)
            ).scalar_one_or_none()
            if order:
                order.status = "paid"

                # Update user stats
                user = session.execute(
                    select(User).where(User.id == order.user_id)
                ).scalar_one_or_none()
                if user:
                    user.total_spent += float(order.final_amount)
                    user.total_orders += 1

            session.commit()
            logger.info(f"Payment {payment_id} verified on-chain")
            return {"status": "confirmed"}

        return {"status": "pending", "message": "Not yet confirmed on-chain"}


def _check_tron_or_bsc(payment, method):
    """Check USDT TRC20/BEP20 payment via public API"""
    import requests

    if not payment.tx_hash and not method.wallet_address:
        return False

    wallet = method.wallet_address
    if not wallet:
        return False

    try:
        if "trc20" in method.code:
            # TronGrid API
            url = f"https://api.trongrid.io/v1/accounts/{wallet}/transactions/trc20"
            params = {"limit": 20, "only_confirmed": "true"}
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for tx in data.get("data", []):
                    # Match amount (USDT has 6 decimals on TRON)
                    value = int(tx.get("value", 0)) / 1_000_000
                    if abs(value - float(payment.amount)) < 0.01:
                        payment.tx_hash = tx.get("transaction_id", "")
                        return True

        elif "bep20" in method.code:
            # BSCScan API
            url = "https://api.bscscan.com/api"
            params = {
                "module": "account",
                "action": "tokentx",
                "address": wallet,
                "sort": "desc",
                "page": 1,
                "offset": 20,
            }
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for tx in data.get("result", []):
                    value = int(tx.get("value", 0)) / (10 ** int(tx.get("tokenDecimal", 18)))
                    if abs(value - float(payment.amount)) < 0.01:
                        payment.tx_hash = tx.get("hash", "")
                        return True

    except Exception as e:
        logger.error(f"Crypto verification error: {e}")

    return False


def _check_btc(payment, method):
    """Check BTC payment via blockchain.info"""
    import requests

    wallet = method.wallet_address
    if not wallet:
        return False

    try:
        url = f"https://blockchain.info/rawaddr/{wallet}?limit=10"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for tx in data.get("txs", []):
                for output in tx.get("out", []):
                    if output.get("addr") == wallet:
                        value_btc = output.get("value", 0) / 100_000_000
                        # Would need BTC price conversion here
                        if payment.tx_hash and payment.tx_hash == tx.get("hash"):
                            return True
    except Exception as e:
        logger.error(f"BTC verification error: {e}")

    return False


@app.task(name="workers.tasks.payment_tasks.process_wallet_deposit")
def process_wallet_deposit(user_id: str, amount: float, method_code: str):
    """Process confirmed deposit into wallet"""
    from models.wallet import Wallet, WalletTransaction
    import uuid

    with Session(engine) as session:
        wallet = session.execute(
            select(Wallet).where(Wallet.user_id == uuid.UUID(user_id))
        ).scalar_one_or_none()

        if not wallet:
            return {"error": "Wallet not found"}

        wallet.balance += amount
        wallet.total_deposited += amount

        session.add(WalletTransaction(
            wallet_id=wallet.id,
            type="deposit",
            amount=amount,
            balance_after=wallet.balance,
            description=f"Deposit via {method_code}",
        ))

        session.commit()
        logger.info(f"Deposited ${amount} to user {user_id}")
        return {"success": True, "balance": float(wallet.balance)}
