"""Wallet handler — balance, deposit with payment methods, history"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
from models.user import User
from models.wallet import Wallet, WalletTransaction
from models.payment import PaymentMethod, Payment

from config import settings
from keyboards import wallet_kb, deposit_amounts_kb, back_kb
from bot_services import admin_notify

router = Router()


class DepositState(StatesGroup):
    custom_amount = State()


# ─── Wallet ──────────────────────────────────────────
@router.message(Command("wallet"))
@router.callback_query(F.data == "menu:wallet")
async def show_wallet(event, session: AsyncSession, lang: str = "en", **kwargs):
    tg_id = event.from_user.id
    user = (await session.execute(select(User).where(User.telegram_id == tg_id))).scalar_one_or_none()
    wallet = (await session.execute(select(Wallet).where(Wallet.user_id == user.id))).scalar_one_or_none() if user else None

    balance = round(wallet.balance, 2) if wallet else 0
    deposited = round(wallet.total_deposited, 2) if wallet else 0
    spent = round(wallet.total_spent, 2) if wallet else 0

    # Visual balance bar
    bar_len = 10
    fill = min(bar_len, int((balance / max(deposited, 1)) * bar_len)) if deposited > 0 else 0
    bar = '▓' * fill + '░' * (bar_len - fill)

    if lang == "ar":
        text = (
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰  <b>محفظتي</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"💵  الرصيد:  <b>${balance:.2f}</b>\n"
            f"     {bar}\n\n"
            f"📥  إجمالي الإيداعات:  <b>${deposited:.2f}</b>\n"
            f"📤  إجمالي المصروفات:  <b>${spent:.2f}</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = (
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰  <b>MY WALLET</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"💵  Balance:  <b>${balance:.2f}</b>\n"
            f"     {bar}\n\n"
            f"📥  Deposited:  <b>${deposited:.2f}</b>\n"
            f"📤  Spent:  <b>${spent:.2f}</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━"
        )

    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=wallet_kb(lang))
        except Exception:
            await event.message.answer(text, reply_markup=wallet_kb(lang))
        await event.answer()
    else:
        await event.answer(text, reply_markup=wallet_kb(lang))


# ─── Deposit (amount selection) ──────────────────────
@router.message(Command("deposit"))
@router.callback_query(F.data == "wallet:deposit")
async def show_deposit(event, session: AsyncSession = None, lang: str = "en", **kwargs):
    if lang == "ar":
        text = (
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💳  <b>إيداع رصيد</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"اختر مبلغ الإيداع بالدولار:\n"
        )
    else:
        text = (
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💳  <b>Deposit Funds</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"Select deposit amount (USD):\n"
        )

    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=deposit_amounts_kb(lang))
        except Exception:
            await event.message.answer(text, reply_markup=deposit_amounts_kb(lang))
        await event.answer()
    else:
        await event.answer(text, reply_markup=deposit_amounts_kb(lang))


# ─── Handle amount selection ─────────────────────────
@router.callback_query(F.data.startswith("deposit_amount:"))
async def handle_deposit_amount(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str = "en", **kwargs):
    val = callback.data.split(":")[1]

    if val == "custom":
        text = "✏️ Enter the amount you want to deposit (USD):" if lang == "en" else "✏️ أدخل المبلغ (بالدولار):"
        await state.set_state(DepositState.custom_amount)
        await callback.message.edit_text(text, reply_markup=back_kb("wallet:deposit", lang))
        await callback.answer()
        return

    amount = float(val)
    await _show_deposit_methods(callback, session, amount, lang)
    await callback.answer()


@router.message(DepositState.custom_amount)
async def handle_custom_deposit(message: Message, session: AsyncSession, state: FSMContext, lang: str = "en", **kwargs):
    await state.clear()
    try:
        amount = float(message.text.strip().replace("$", ""))
        if amount < 1:
            raise ValueError
    except ValueError:
        await message.answer("❌ Invalid amount. Minimum $1." if lang == "en" else "❌ مبلغ غير صالح. الحد الأدنى $1.")
        return

    await _show_deposit_methods(message, session, amount, lang)


async def _show_deposit_methods(event, session: AsyncSession, amount: float, lang: str):
    """Show available payment methods for deposit."""
    methods = (await session.execute(
        select(PaymentMethod).where(
            PaymentMethod.is_enabled == True,
            PaymentMethod.is_deleted == False,
            PaymentMethod.code != "wallet",
        ).order_by(PaymentMethod.sort_order)
    )).scalars().all()

    if not methods:
        text = "❌ No payment methods available." if lang == "en" else "❌ لا توجد طرق دفع متاحة."
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text, reply_markup=back_kb("wallet:deposit", lang))
        else:
            await event.answer(text, reply_markup=back_kb("wallet:deposit", lang))
        return

    builder = InlineKeyboardBuilder()
    icons = {"usdt_trc20": "💎", "usdt_bep20": "💎", "btc": "₿", "binance_uid": "💫", "vodafone": "📱", "instapay": "🏦"}

    for m in methods:
        icon = icons.get(m.code, "💳")
        builder.row(InlineKeyboardButton(
            text=f"{icon} {m.name} — ${amount:.2f}",
            callback_data=f"dep_pay:{amount}:{m.code}",
        ))

    builder.row(InlineKeyboardButton(
        text="⬅️ Back" if lang == "en" else "⬅️ رجوع",
        callback_data="wallet:deposit",
    ))

    if lang == "ar":
        text = (
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💳  <b>إيداع ${amount:.2f}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"اختر طريقة الدفع:\n"
        )
    else:
        text = (
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💳  <b>Deposit ${amount:.2f}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"Choose a payment method:\n"
        )

    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await msg.edit_text(text, reply_markup=builder.as_markup())
    else:
        await msg.answer(text, reply_markup=builder.as_markup())


# ─── Handle deposit payment ──────────────────────────
@router.callback_query(F.data.startswith("dep_pay:"))
async def handle_deposit_payment(callback: CallbackQuery, session: AsyncSession, lang: str = "en", **kwargs):
    parts = callback.data.split(":")
    amount = float(parts[1])
    method_code = parts[2]

    method = (await session.execute(
        select(PaymentMethod).where(PaymentMethod.code == method_code)
    )).scalar_one_or_none()

    if not method:
        await callback.answer("Payment method not found", show_alert=True)
        return

    user = (await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )).scalar_one_or_none()

    if not user:
        await callback.answer("User not found", show_alert=True)
        return

    # Create a deposit payment record
    import uuid
    deposit_ref = f"DEP-{uuid.uuid4().hex[:8].upper()}"

    session.add(Payment(
        order_id=None,  # No order — just a deposit
        user_id=user.id,
        method_code=method_code,
        amount=amount,
        currency="USD",
        status="pending",
        verification_type="note",
        tx_note=deposit_ref,
    ))
    await session.commit()

    # ── Admin notify ──
    await admin_notify.deposit_request(callback.from_user, amount, method.name, ref_id=deposit_ref)

    wallet_addr = method.wallet_address or "Contact admin for address"
    timeout = settings.PAYMENT_TIMEOUT_MINUTES

    if "binance" in method_code.lower():
        text = (
            f"💫 <b>Deposit via {method.name}</b>\n\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"💰 Amount: <b>${amount:.2f}</b>\n"
            f"🆔 Binance ID: <code>{wallet_addr}</code>\n"
            f"📝 Note: <code>{deposit_ref}</code>\n\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"<b>Instructions:</b>\n"
            f"1. Open Binance app\n"
            f"2. Go to Send → Pay\n"
            f"3. Enter ID: <code>{wallet_addr}</code>\n"
            f"4. Amount: <code>{amount:.2f}</code> USDT\n"
            f"5. Add note: <code>{deposit_ref}</code>\n"
            f"6. Confirm & press 'I Paid' below\n\n"
            f"⏰ Complete within {timeout} minutes"
        ) if lang == "en" else (
            f"💫 <b>إيداع عبر {method.name}</b>\n\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"💰 المبلغ: <b>${amount:.2f}</b>\n"
            f"🆔 Binance ID: <code>{wallet_addr}</code>\n"
            f"📝 ملاحظة: <code>{deposit_ref}</code>\n\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"<b>التعليمات:</b>\n"
            f"1. افتح تطبيق Binance\n"
            f"2. اذهب إلى إرسال → دفع\n"
            f"3. أدخل ID: <code>{wallet_addr}</code>\n"
            f"4. المبلغ: <code>{amount:.2f}</code> USDT\n"
            f"5. أضف الملاحظة: <code>{deposit_ref}</code>\n"
            f"6. أكد واضغط 'دفعت' بالأسفل\n\n"
            f"⏰ أكمل خلال {timeout} دقيقة"
        )
    else:
        text = (
            f"💳 <b>Deposit via {method.name}</b>\n\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"💰 Amount: <b>${amount:.2f}</b>\n"
            f"📋 Address: <code>{wallet_addr}</code>\n"
            f"📝 Reference: <code>{deposit_ref}</code>\n\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"Send exactly <b>${amount:.2f}</b> to the address above.\n"
            f"Include the reference in your note/memo.\n\n"
            f"⏰ Complete within {timeout} minutes"
        ) if lang == "en" else (
            f"💳 <b>إيداع عبر {method.name}</b>\n\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"💰 المبلغ: <b>${amount:.2f}</b>\n"
            f"📋 العنوان: <code>{wallet_addr}</code>\n"
            f"📝 المرجع: <code>{deposit_ref}</code>\n\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"أرسل بالضبط <b>${amount:.2f}</b> إلى العنوان أعلاه.\n"
            f"أضف المرجع في الملاحظات.\n\n"
            f"⏰ أكمل خلال {timeout} دقيقة"
        )

    # I Paid + Cancel buttons
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="✅ I Paid" if lang == "en" else "✅ دفعت",
        callback_data=f"dep_confirm:{deposit_ref}",
    ))
    builder.row(InlineKeyboardButton(
        text="❌ Cancel" if lang == "en" else "❌ إلغاء",
        callback_data="wallet:deposit",
    ))

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


# ─── Deposit confirmation (I Paid) ───────────────────
@router.callback_query(F.data.startswith("dep_confirm:"))
async def handle_deposit_confirm(callback: CallbackQuery, session: AsyncSession, lang: str = "en", **kwargs):
    deposit_ref = callback.data.split(":")[1]

    # Look up the payment record
    payment = (await session.execute(
        select(Payment).where(
            Payment.tx_note == deposit_ref,
            Payment.order_id == None,
        )
    )).scalar_one_or_none()

    if not payment:
        await callback.answer("Deposit not found.", show_alert=True)
        return

    # Already confirmed (maybe by background poller)
    if payment.status == "confirmed":
        user = (await session.execute(
            select(User).where(User.id == payment.user_id)
        )).scalar_one_or_none()
        wallet = (await session.execute(
            select(Wallet).where(Wallet.user_id == user.id)
        )).scalar_one_or_none() if user else None
        balance = round(wallet.balance, 2) if wallet else 0

        text = (
            f"✅ <b>Deposit Confirmed!</b>\n\n"
            f"💰 Amount: <b>${payment.amount:.2f}</b>\n"
            f"🆔 Reference: <code>{deposit_ref}</code>\n"
            f"💵 New Balance: <b>${balance}</b>\n\n"
            f"Your wallet has been credited. 🎉"
        ) if lang == "en" else (
            f"✅ <b>تم تأكيد الإيداع!</b>\n\n"
            f"💰 المبلغ: <b>${payment.amount:.2f}</b>\n"
            f"🆔 المرجع: <code>{deposit_ref}</code>\n"
            f"💵 الرصيد الجديد: <b>${balance}</b>\n\n"
            f"تم إضافة الرصيد لمحفظتك. 🎉"
        )
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text="💰 My Wallet" if lang == "en" else "💰 محفظتي",
            callback_data="menu:wallet",
        ))
        builder.row(InlineKeyboardButton(
            text="🛍 Shop Now" if lang == "en" else "🛍 تسوق الآن",
            callback_data="menu:products",
        ))
        try:
            await callback.message.edit_text(text, reply_markup=builder.as_markup())
        except Exception:
            pass
        await callback.answer()
        return

    # For Binance payments, trigger an immediate check
    if "binance" in payment.method_code.lower():
        from dotenv import load_dotenv
        import os as _os
        _bot_dir = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
        load_dotenv(_os.path.join(_bot_dir, ".env"))
        b_key = _os.environ.get("BINANCE_API_KEY", "")
        b_secret = _os.environ.get("BINANCE_API_SECRET", "")
        b_uid = _os.environ.get("BINANCE_UID", "")

        if b_key and b_secret:
            from bot_services.binance_checker import BinanceChecker
            checker = BinanceChecker(b_key, b_secret, b_uid)
            tx = await checker.check_single_deposit(session, deposit_ref, payment.amount)

            if tx:
                # ✅ Payment found! Confirm deposit and credit wallet
                tx_id = str(tx.get("transactionId", tx.get("orderNo", tx.get("tranId", ""))))
                await checker._confirm_deposit(session, payment, tx_id, bot=None)

                # Refresh wallet balance
                user = (await session.execute(
                    select(User).where(User.id == payment.user_id)
                )).scalar_one_or_none()
                wallet = (await session.execute(
                    select(Wallet).where(Wallet.user_id == user.id)
                )).scalar_one_or_none() if user else None

                balance = round(wallet.balance, 2) if wallet else 0

                text = (
                    f"✅ <b>Deposit Confirmed!</b>\n\n"
                    f"💰 Amount: <b>${payment.amount:.2f}</b>\n"
                    f"🆔 Reference: <code>{deposit_ref}</code>\n"
                    f"💵 New Balance: <b>${balance}</b>\n\n"
                    f"Your wallet has been credited automatically. 🎉"
                ) if lang == "en" else (
                    f"✅ <b>تم تأكيد الإيداع!</b>\n\n"
                    f"💰 المبلغ: <b>${payment.amount:.2f}</b>\n"
                    f"🆔 المرجع: <code>{deposit_ref}</code>\n"
                    f"💵 الرصيد الجديد: <b>${balance}</b>\n\n"
                    f"تم إضافة الرصيد لمحفظتك تلقائياً. 🎉"
                )

                builder = InlineKeyboardBuilder()
                builder.row(InlineKeyboardButton(
                    text="💰 My Wallet" if lang == "en" else "💰 محفظتي",
                    callback_data="menu:wallet",
                ))
                builder.row(InlineKeyboardButton(
                    text="🛍 Shop Now" if lang == "en" else "🛍 تسوق الآن",
                    callback_data="menu:products",
                ))

                await callback.message.edit_text(text, reply_markup=builder.as_markup())
                await callback.answer("✅ Payment confirmed!" if lang == "en" else "✅ تم تأكيد الدفع!", show_alert=True)
                return

            else:
                # ❌ Payment NOT found — show popup alert, do NOT navigate away
                # User stays on the same payment instructions screen with I Paid button
                await callback.answer(
                    "⏳ Payment not detected yet.\n\n"
                    "Make sure you:\n"
                    "1. Sent the correct amount\n"
                    "2. Added the correct note\n"
                    "3. Wait a moment and try again\n\n"
                    "🔄 Auto-checking every 10 seconds..."
                    if lang == "en" else
                    "⏳ لم يتم اكتشاف الدفع بعد.\n\n"
                    "تأكد من:\n"
                    "1. إرسال المبلغ الصحيح\n"
                    "2. إضافة النوت الصحيحة\n"
                    "3. انتظر لحظة وحاول مرة أخرى\n\n"
                    "🔄 فحص تلقائي كل 10 ثواني...",
                    show_alert=True
                )
                return
        else:
            # Binance not configured — just show alert
            await callback.answer(
                "⚠️ Binance API not configured. Admin will review manually."
                if lang == "en" else
                "⚠️ Binance API غير مُعد. سيراجع الأدمن يدوياً.",
                show_alert=True
            )
            return

    # Non-Binance payment — show popup alert, stay on same page
    await callback.answer(
        "✅ Payment noted! Admin will review and approve shortly.\n"
        "You'll receive a notification when confirmed."
        if lang == "en" else
        "✅ تم تسجيل الدفع! سيراجع الأدمن ويوافق قريباً.\n"
        "ستتلقى إشعاراً عند التأكيد.",
        show_alert=True
    )


# ─── TOPUP (same as deposit) ─────────────────────────
@router.callback_query(F.data == "menu:topup")
async def show_topup(callback: CallbackQuery, session: AsyncSession, lang: str = "en", **kwargs):
    await show_deposit(callback, session, lang)


# ─── History ─────────────────────────────────────────
@router.callback_query(F.data == "wallet:history")
async def show_history(callback: CallbackQuery, session: AsyncSession, lang: str = "en", **kwargs):
    user = (await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )).scalar_one_or_none()
    wallet = (await session.execute(select(Wallet).where(Wallet.user_id == user.id))).scalar_one_or_none()

    if not wallet:
        await callback.answer("No transactions", show_alert=True)
        return

    txns = (await session.execute(
        select(WalletTransaction).where(WalletTransaction.wallet_id == wallet.id)
        .order_by(desc(WalletTransaction.created_at)).limit(10)
    )).scalars().all()

    if not txns:
        text = (
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊  <b>Transaction History</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"No transactions yet."
        )
    else:
        lines = [
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊  <b>Transaction History</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
        ]
        for t in txns:
            icon = "🟢" if t.amount > 0 else "🔴"
            sign = "+" if t.amount > 0 else ""
            date_str = t.created_at.strftime("%m/%d %H:%M") if t.created_at else ""
            lines.append(
                f"{icon} <b>{sign}${abs(t.amount):.2f}</b>  →  ${t.balance_after:.2f}\n"
                f"    <i>{t.description or '—'}</i>  •  {date_str}"
            )
        text = "\n".join(lines)

    try:
        await callback.message.edit_text(text, reply_markup=back_kb("menu:wallet", lang))
    except Exception:
        await callback.message.answer(text, reply_markup=back_kb("menu:wallet", lang))
    await callback.answer()
