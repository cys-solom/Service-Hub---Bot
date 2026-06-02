"""Binance Pay Auto-Verification Service

Polls Binance Pay transaction history to match pending payments by order note.
When a matching payment is found, auto-confirms and triggers delivery.
Also handles deposit payments (wallet top-up) automatically.

Setup:
1. Add these to .env:
   BINANCE_API_KEY=your_api_key
   BINANCE_API_SECRET=your_api_secret
   BINANCE_UID=your_binance_uid

2. Create a Binance API Key:
   - Go to Binance → Settings → API Management
   - Create API → Choose "System generated"
   - Enable "Enable Reading" ONLY (no other permissions needed!)
   - Save API Key + Secret
"""
import asyncio
import hashlib
import hmac
import time
import logging
from datetime import datetime, timedelta, timezone

import aiohttp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
from models.order import Order, OrderItem
from models.payment import Payment
from models.stock import StockItem
from models.user import User
from models.wallet import Wallet, WalletTransaction

logger = logging.getLogger(__name__)

BINANCE_API_URL = "https://api.binance.com"
POLL_INTERVAL = 10  # seconds — check every 10s


class BinanceChecker:
    def __init__(self, api_key: str, api_secret: str, binance_uid: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.binance_uid = binance_uid
        self._running = False
        self._time_offset = 0  # Offset between local and Binance server time

    def _sign(self, params: dict) -> str:
        """Create HMAC SHA256 signature"""
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return hmac.new(
            self.api_secret.encode(), query.encode(), hashlib.sha256
        ).hexdigest()

    async def _sync_time(self):
        """Sync local time with Binance server time"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BINANCE_API_URL}/api/v3/time") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        server_time = data["serverTime"]
                        local_time = int(time.time() * 1000)
                        self._time_offset = server_time - local_time
                        logger.info(f"[Binance] Time offset: {self._time_offset}ms")
        except Exception as e:
            logger.warning(f"[Binance] Time sync failed: {e}")

    def _get_timestamp(self) -> int:
        """Get Binance-synced timestamp"""
        return int(time.time() * 1000) + self._time_offset

    async def get_pay_transactions(self, start_time: int = None) -> list[dict]:
        """Get recent Binance Pay transactions (incoming payments via UID)
        
        Uses /sapi/v1/pay/transactions — requires only 'Enable Reading' permission.
        No IP restriction or Universal Transfer needed!
        """
        if not start_time:
            # Last 2 hours
            start_time = int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp() * 1000)

        query = f"timestamp={self._get_timestamp()}&recvWindow=30000&startTime={start_time}"
        sig = hmac.new(
            self.api_secret.encode(), query.encode(), hashlib.sha256
        ).hexdigest()
        url = f"{BINANCE_API_URL}/sapi/v1/pay/transactions?{query}&signature={sig}"
        headers = {"X-MBX-APIKEY": self.api_key}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        transactions = data.get("data", [])
                        # Filter only RECEIVED payments (amount > 0 means incoming)
                        received = [t for t in transactions
                                    if float(t.get("amount", 0)) > 0]
                        logger.debug(f"[Binance] Found {len(received)} incoming pay transactions")
                        return received
                    else:
                        text = await resp.text()
                        logger.warning(f"[Binance] Pay API error: {resp.status} — {text}")
                        return []
        except Exception as e:
            logger.error(f"[Binance] API connection error: {e}")
            return []

    async def get_transfer_history(self, start_time: int = None) -> list[dict]:
        """Fallback: Get internal transfer history (requires Universal Transfer permission)"""
        if not start_time:
            start_time = int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp() * 1000)

        query = f"type=MAIN_FUNDING&startTime={start_time}&timestamp={self._get_timestamp()}&recvWindow=30000"
        sig = hmac.new(
            self.api_secret.encode(), query.encode(), hashlib.sha256
        ).hexdigest()
        url = f"{BINANCE_API_URL}/sapi/v1/asset/transfer?{query}&signature={sig}"
        headers = {"X-MBX-APIKEY": self.api_key}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("rows", [])
                    else:
                        return []
        except Exception:
            return []

    def _match_transaction_by_note(self, transaction: dict, note: str, expected_amount: float) -> bool:
        """Check if a Binance Pay transaction matches by note and amount"""
        # Check note/remark
        tx_note = str(transaction.get("note", "") or transaction.get("orderInfo", ""))
        
        # Check amount (in the funds array)
        total_amount = 0
        for fund in transaction.get("funds", []):
            if fund.get("currency", "").upper() in ("USDT", "BUSD", "USD"):
                total_amount += abs(float(fund.get("amount", 0)))

        # Also check direct amount field
        if total_amount == 0:
            total_amount = abs(float(transaction.get("amount", 0)))

        matched = (
            note.upper() in tx_note.upper()
            and total_amount >= expected_amount * 0.99  # 1% tolerance
        )

        if matched:
            logger.info(f"[Binance] ✅ Match found: note='{tx_note}', amount={total_amount}, expected_note={note}")

        return matched

    # Keep backward compat alias
    def _match_pay_transaction(self, transaction: dict, order_number: str, expected_amount: float) -> bool:
        return self._match_transaction_by_note(transaction, order_number, expected_amount)

    def _match_transfer(self, transfer: dict, order_number: str, expected_amount: float) -> bool:
        """Check if a universal transfer matches an order"""
        note = str(transfer.get("clientTranId", "")) or str(transfer.get("tranId", ""))
        amount = float(transfer.get("amount", 0))
        return order_number.upper() in note.upper() and amount >= expected_amount * 0.99

    async def check_single_deposit(self, db_session: AsyncSession, deposit_ref: str, expected_amount: float) -> dict | None:
        """Check if a specific deposit has been received on Binance.
        Returns the matching transaction dict if found, None otherwise.
        """
        await self._sync_time()
        
        pay_transactions = await self.get_pay_transactions()
        
        for tx in pay_transactions:
            if self._match_transaction_by_note(tx, deposit_ref, expected_amount):
                return tx

        # Fallback: check transfer history
        transfers = await self.get_transfer_history()
        for transfer in transfers:
            if self._match_transfer(transfer, deposit_ref, expected_amount):
                return transfer

        return None

    async def _confirm_deposit(self, session: AsyncSession, payment: Payment, tx_id: str, bot=None):
        """Confirm a deposit payment and credit user's wallet."""
        payment.status = "confirmed"
        payment.tx_hash = tx_id
        payment.confirmed_at = datetime.now(timezone.utc).isoformat()

        # Get user
        user = (await session.execute(
            select(User).where(User.id == payment.user_id)
        )).scalar_one_or_none()

        if not user:
            logger.warning(f"[Binance] User not found for deposit {payment.tx_note}")
            await session.commit()
            return

        # Get or create wallet
        wallet = (await session.execute(
            select(Wallet).where(Wallet.user_id == user.id)
        )).scalar_one_or_none()

        if not wallet:
            wallet = Wallet(user_id=user.id, balance=0, total_deposited=0, total_spent=0)
            session.add(wallet)
            await session.flush()

        before = wallet.balance
        wallet.balance += payment.amount
        wallet.total_deposited += payment.amount

        # Record transaction
        session.add(WalletTransaction(
            wallet_id=wallet.id, type="deposit", amount=payment.amount,
            balance_before=before, balance_after=wallet.balance,
            description=f"Binance deposit (ref: {payment.tx_note})",
            reference_id=str(payment.id),
        ))

        await session.commit()

        logger.info(
            f"[Binance] ✅ Deposit confirmed: ${payment.amount} for "
            f"{user.username or user.telegram_id} (ref: {payment.tx_note})"
        )

        # Notify user via Telegram
        if bot and user.telegram_id:
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            from aiogram.types import InlineKeyboardButton

            text = (
                f"✅ <b>Deposit Confirmed!</b>\n\n"
                f"💰 Amount: <b>${payment.amount:.2f}</b>\n"
                f"🆔 Reference: <code>{payment.tx_note}</code>\n"
                f"💵 New Balance: <b>${wallet.balance:.2f}</b>\n\n"
                f"Your wallet has been credited automatically. 🎉"
            )

            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(
                text="💰 My Wallet",
                callback_data="menu:wallet",
            ))
            builder.row(InlineKeyboardButton(
                text="🛍 Shop Now",
                callback_data="menu:products",
            ))

            try:
                await bot.send_message(
                    user.telegram_id, text,
                    reply_markup=builder.as_markup()
                )
            except Exception as e:
                logger.warning(f"[Binance] Failed to notify user {user.telegram_id}: {e}")

    async def poll_pending_payments(self, get_session_func, bot=None):
        """Background polling loop — checks all pending Binance payments (orders + deposits)"""
        self._running = True
        logger.info(f"[Binance] Payment checker started — polling every {POLL_INTERVAL}s")

        while self._running:
            await self._sync_time()
            try:
                async with get_session_func() as session:
                    # Get ALL pending Binance payments (both orders and deposits)
                    pending = (await session.execute(
                        select(Payment).where(
                            Payment.status == "pending",
                            Payment.method_code.in_(["binance_uid", "binance_pay"]),
                        )
                    )).scalars().all()

                    if pending:
                        # Fetch transactions once for all pending payments
                        pay_transactions = await self.get_pay_transactions()
                        transfers = await self.get_transfer_history()

                        pending_orders = [p for p in pending if p.order_id is not None]
                        pending_deposits = [p for p in pending if p.order_id is None]

                        logger.info(
                            f"[Binance] Checking {len(pending_orders)} order payments + "
                            f"{len(pending_deposits)} deposits against "
                            f"{len(pay_transactions)} pay txns + {len(transfers)} transfers"
                        )

                        # ── Process ORDER payments ──
                        for payment in pending_orders:
                            order = (await session.execute(
                                select(Order).where(Order.id == payment.order_id)
                            )).scalar_one_or_none()

                            if not order:
                                continue

                            if order.status == "canceled":
                                payment.status = "expired"
                                continue

                            matched = False
                            tx_id = ""

                            for tx in pay_transactions:
                                if self._match_pay_transaction(tx, order.order_number, payment.amount):
                                    matched = True
                                    tx_id = str(tx.get("transactionId", tx.get("orderNo", "")))
                                    break

                            if not matched:
                                for transfer in transfers:
                                    if self._match_transfer(transfer, order.order_number, payment.amount):
                                        matched = True
                                        tx_id = str(transfer.get("tranId", ""))
                                        break

                            if matched:
                                logger.info(f"[Binance] ✅ Payment confirmed for order {order.order_number}")
                                payment.status = "confirmed"
                                payment.tx_hash = tx_id
                                payment.confirmed_at = datetime.now(timezone.utc).isoformat()

                                order.status = "paid"
                                order.payment_method = payment.method_code

                                user = (await session.execute(
                                    select(User).where(User.id == order.user_id)
                                )).scalar_one_or_none()
                                if user:
                                    user.total_spent += order.final_amount
                                    user.total_orders += 1

                                await session.commit()

                                if bot:
                                    await self._auto_deliver(session, order, user, bot)

                        # ── Process DEPOSIT payments ──
                        for payment in pending_deposits:
                            note = payment.tx_note  # DEP-XXXXXXXX
                            if not note:
                                continue

                            matched = False
                            tx_id = ""

                            for tx in pay_transactions:
                                if self._match_transaction_by_note(tx, note, payment.amount):
                                    matched = True
                                    tx_id = str(tx.get("transactionId", tx.get("orderNo", "")))
                                    break

                            if not matched:
                                for transfer in transfers:
                                    if self._match_transfer(transfer, note, payment.amount):
                                        matched = True
                                        tx_id = str(transfer.get("tranId", ""))
                                        break

                            if matched:
                                await self._confirm_deposit(session, payment, tx_id, bot)

                    await session.commit()

            except Exception as e:
                logger.error(f"[Binance] Polling error: {e}", exc_info=True)

            await asyncio.sleep(POLL_INTERVAL)

    async def _auto_deliver(self, session: AsyncSession, order, user, bot):
        """Auto-deliver stock items after payment confirmation"""
        try:
            # Get reserved stock
            result = await session.execute(
                select(StockItem).where(
                    StockItem.order_id == order.id,
                    StockItem.is_reserved == True,
                )
            )
            items = result.scalars().all()

            delivery_data = []
            for item in items:
                item.is_sold = True
                item.is_reserved = False
                item.sold_to = order.user_id
                delivery_data.append(item.data)

            # Update order items
            oi_result = await session.execute(
                select(OrderItem).where(OrderItem.order_id == order.id)
            )
            for oi in oi_result.scalars().all():
                oi.status = "delivered"
                oi.delivered_data = "\n".join(delivery_data)

            order.status = "delivered"
            order.delivery_data = {"items": delivery_data}
            await session.commit()

            # Auto-credit referral commission
            try:
                from bot_services.referral_commission import credit_referral_commission
                await credit_referral_commission(session, order.user_id, order.final_amount)
            except Exception as e:
                logger.warning(f"[Binance] Referral commission error: {e}")

            # Send delivery message to user
            if user and user.telegram_id:
                delivery_text = "\n".join([f"<code>{d}</code>" for d in delivery_data])
                text = (
                    f"✅ <b>Payment Confirmed & Delivered!</b>\n\n"
                    f"📦 Order: <b>{order.order_number}</b>\n\n"
                    f"📋 Your data:\n{delivery_text}\n\n"
                    f"Thank you for shopping! 🎉"
                )
                await bot.send_message(user.telegram_id, text)

        except Exception as e:
            logger.error(f"[Binance] Auto-delivery error for {order.order_number}: {e}")

    def stop(self):
        self._running = False

