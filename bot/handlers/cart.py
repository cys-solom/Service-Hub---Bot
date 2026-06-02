"""Cart / Purchase handler — MMO Store style with CMS templates + Binance + Coupons"""
import uuid
from datetime import datetime, timezone
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
from models.catalog import Product, ProductPrice
from models.stock import StockItem
from models.order import Order, OrderItem
from models.payment import PaymentMethod, Payment
from models.user import User
from models.wallet import Wallet, WalletTransaction
from models.coupon import Coupon

from config import settings
from keyboards import payment_methods_kb, payment_cancel_kb, back_kb, main_menu_inline_kb, product_detail_kb, order_summary_kb
from bot_services import cms
from bot_services.referral_commission import credit_referral_commission
from bot_services import admin_notify

router = Router()


class CustomQtyState(StatesGroup):
    waiting_qty = State()


class CouponState(StatesGroup):
    waiting_code = State()


class ApiInputState(StatesGroup):
    waiting_email   = State()
    waiting_confirm = State()   # emails stored in FSM, awaiting user confirmation


def _short_order_id():
    return f"ORDER{uuid.uuid4().hex[:5].upper()}"

def _sid(uid):
    """Strip dashes from UUID for short callback data"""
    return str(uid).replace('-', '')

def _eid(short):
    """Expand dashless hex back to UUID string"""
    h = short.strip()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"

async def _get_order_product(session, order):
    """Get the product from order items"""
    oi = (await session.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().first()
    if not oi:
        return None
    return (await session.execute(select(Product).where(Product.id == oi.product_id))).scalar_one_or_none()


@router.callback_query(F.data.startswith("qty:"))
async def handle_quantity(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str = "en"):
    parts = callback.data.split(":")
    product_id, qty = parts[1], int(parts[2])

    # Check if this is an API-delivery product
    product = (await session.execute(select(Product).where(Product.id == product_id))).scalar_one_or_none()
    if product and (product.meta or {}).get("delivery_type") == "api":
        meta = product.meta or {}
        price_row = (await session.execute(
            select(ProductPrice).where(ProductPrice.product_id == product.id, ProductPrice.is_deleted == False).limit(1)
        )).scalar_one_or_none()
        unit_price = price_row.price if price_row else 0
        await _ask_api_emails(callback.message, state, product_id, unit_price, lang)
        await callback.answer()
        return

    await _create_order(callback, session, product_id, qty, lang)


async def _ask_api_emails(msg, state: FSMContext, product_id: str, unit_price: float, lang: str):
    """Show email input prompt for API products — supports multi-email"""
    await state.set_state(ApiInputState.waiting_email)
    await state.update_data(product_id=product_id, unit_price=unit_price)
    if lang == "ar":
        text = (
            "📧 <b>أدخل البريد الإلكتروني</b>\n"
            "━━━━━━━━━━━━━━━\n\n"
            "يمكنك إدخال أكثر من بريد — <b>كل بريد في سطر منفصل</b>\n"
            f"💡 كل بريد = شهر واحد = <b>${unit_price:.2f}</b>\n\n"
            "<i>مثال:</i>\n"
            "<code>user1@gmail.com\nuser2@gmail.com</code>"
        )
    else:
        text = (
            "📧 <b>Enter Email Address(es)</b>\n"
            "━━━━━━━━━━━━━━━\n\n"
            "You can enter multiple emails — <b>one per line</b>\n"
            f"💡 Each email = 1 month = <b>${unit_price:.2f}</b>\n\n"
            "<i>Example:</i>\n"
            "<code>user1@gmail.com\nuser2@gmail.com</code>"
        )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="❌ Cancel" if lang == "en" else "❌ إلغاء",
        callback_data="menu:products"
    ))
    try:
        await msg.edit_text(text, reply_markup=builder.as_markup())
    except Exception:
        await msg.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("qty_custom:"))
async def handle_custom_qty_prompt(callback: CallbackQuery, state: FSMContext, session: AsyncSession, lang: str = "en"):
    product_id = callback.data.split(":")[1]
    # Check if API product — send to email prompt instead
    product = (await session.execute(select(Product).where(Product.id == product_id))).scalar_one_or_none()
    if product and (product.meta or {}).get("delivery_type") == "api":
        price_row = (await session.execute(
            select(ProductPrice).where(ProductPrice.product_id == product.id, ProductPrice.is_deleted == False).limit(1)
        )).scalar_one_or_none()
        unit_price = price_row.price if price_row else 0
        await _ask_api_emails(callback.message, state, product_id, unit_price, lang)
        await callback.answer()
        return
    await state.set_state(CustomQtyState.waiting_qty)
    await state.update_data(product_id=product_id)
    text = "✏️ Enter the quantity you want to buy:" if lang == "en" else "✏️ أدخل الكمية المطلوبة:"
    await callback.message.edit_text(text, reply_markup=back_kb("menu:products", lang))
    await callback.answer()


@router.message(CustomQtyState.waiting_qty)
async def handle_custom_qty_input(message: Message, state: FSMContext, session: AsyncSession, lang: str = "en"):
    data = await state.get_data()
    product_id = data.get("product_id")
    await state.clear()
    try:
        qty = int(message.text.strip())
        if qty < 1:
            raise ValueError
    except ValueError:
        await message.answer("❌ Invalid quantity." if lang == "en" else "❌ كمية غير صالحة.")
        return
    await _create_order(message, session, product_id, qty, lang)


@router.message(ApiInputState.waiting_email)
async def recv_api_email(message: Message, state: FSMContext, session: AsyncSession, lang: str = "en"):
    """Receive one or more emails for API product activation (one per line)"""
    raw = message.text.strip() if message.text else ""
    lines = [l.strip() for l in raw.splitlines() if l.strip()]

    # Validate all emails
    bad = [l for l in lines if "@" not in l or "." not in l]
    if not lines:
        err = "❌ Please enter at least one email." if lang == "en" \
              else "❌ أدخل بريداً إلكترونياً واحداً على الأقل."
        await message.answer(err)
        return
    if bad:
        err = ("❌ Invalid email(s):\n" + "\n".join(f"• {b}" for b in bad)) if lang == "en" \
              else ("❌ بريد غير صالح:\n" + "\n".join(f"• {b}" for b in bad))
        await message.answer(err)
        return

    data        = await state.get_data()
    product_id  = data["product_id"]
    unit_price  = float(data.get("unit_price", 0))
    qty         = len(lines)
    total       = round(unit_price * qty, 2)

    # ── Store emails in FSM state (avoids Telegram's 64-byte callback_data limit) ──
    await state.set_state(ApiInputState.waiting_confirm)
    await state.update_data(emails=lines, qty=qty, total=total)

    emails_joined = "\n".join(f"📧 {e}" for e in lines)
    if lang == "ar":
        confirm_text = (
            f"✅ <b>تأكيد الطلب</b>\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"📬 <b>البريدات الإلكترونية ({qty}):</b>\n{emails_joined}\n\n"
            f"💲 <b>السعر:</b> {qty} × ${unit_price:.2f} = <b>${total:.2f}</b>\n\n"
            "هل تريد المتابعة للدفع؟"
        )
    else:
        confirm_text = (
            f"✅ <b>Order Confirmation</b>\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"📬 <b>Emails ({qty}):</b>\n{emails_joined}\n\n"
            f"💲 <b>Price:</b> {qty} × ${unit_price:.2f} = <b>${total:.2f}</b>\n\n"
            "Proceed to payment?"
        )

    # ── Short callback_data — emails come from FSM state, not callback ──
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="✅ Confirm & Pay" if lang == "en" else "✅ تأكيد والدفع",
        callback_data=f"api_confirm:{product_id}"          # max ~48 bytes ✓
    ))
    builder.row(InlineKeyboardButton(
        text="✏️ Re-enter" if lang == "en" else "✏️ إعادة الإدخال",
        callback_data=f"api_reenter:{product_id}"          # max ~48 bytes ✓
    ))
    await message.answer(confirm_text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("api_reenter:"))
async def api_reenter(callback: CallbackQuery, state: FSMContext, session: AsyncSession, lang: str = "en"):
    product_id = callback.data.split(":")[1]
    price_row = (await session.execute(
        select(ProductPrice).where(ProductPrice.product_id == product_id, ProductPrice.is_deleted == False).limit(1)
    )).scalar_one_or_none()
    unit_price = price_row.price if price_row else 0
    await _ask_api_emails(callback.message, state, product_id, unit_price, lang)
    await callback.answer()


@router.callback_query(F.data.startswith("api_confirm:"))
async def api_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession, lang: str = "en"):
    """User confirmed emails — read from FSM state, create order"""
    product_id = callback.data.split(":")[1]

    # ── Get emails from FSM state (NOT from callback_data) ──
    fsm_data = await state.get_data()
    emails   = fsm_data.get("emails", [])
    qty      = fsm_data.get("qty", len(emails))
    await state.clear()

    if not emails:
        await callback.answer(
            "❌ Session expired. Please start again." if lang == "en"
            else "❌ انتهت الجلسة. ابدأ من جديد.",
            show_alert=True
        )
        return

    await _create_order(callback, session, product_id, qty, lang, api_emails=emails)


# ─── Coupon Flow (applied after order creation) ──────
@router.callback_query(F.data.startswith("coupon:"))
async def coupon_prompt(callback: CallbackQuery, state: FSMContext, lang: str = "en"):
    """Prompt user to enter a coupon code for an existing order"""
    order_sid = callback.data.split(":")[1]
    order_id = _eid(order_sid)
    await state.set_state(CouponState.waiting_code)
    await state.update_data(order_id=order_id)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="❌ Cancel" if lang == "en" else "❌ إلغاء",
        callback_data=f"skipcpn:{order_sid}",
    ))

    text = (
        "🎟 <b>Enter Coupon Code</b>\n\n"
        "Type your coupon code below to get a discount on your order:"
    ) if lang == "en" else (
        "🎟 <b>أدخل كود الكوبون</b>\n\n"
        "اكتب كود الكوبون بالأسفل للحصول على خصم على طلبك:"
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("skipcpn:"))
async def skip_coupon(callback: CallbackQuery, state: FSMContext, session: AsyncSession, lang: str = "en"):
    """User cancelled coupon entry — go back to order summary"""
    await state.clear()
    order_id = _eid(callback.data.split(":")[1])
    order = (await session.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order:
        await callback.answer("Order not found", show_alert=True)
        return
    await _show_order_summary(callback, session, order, lang)


@router.callback_query(F.data.startswith("gopay:"))
async def proceed_to_payment(callback: CallbackQuery, session: AsyncSession, lang: str = "en"):
    """User chose Pay Now — show payment methods"""
    order_id = _eid(callback.data.split(":")[1])
    order = (await session.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order:
        await callback.answer("Order not found", show_alert=True)
        return
    await _show_payment_methods(callback, session, order, lang)


@router.message(CouponState.waiting_code)
async def coupon_validate(message: Message, state: FSMContext, session: AsyncSession, lang: str = "en"):
    """Validate coupon code and apply discount to existing order"""
    data = await state.get_data()
    order_id = data.get("order_id")
    await state.clear()

    code = message.text.strip().upper()

    # Get the order
    order = (await session.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order:
        await message.answer("❌ Order not found.")
        return

    # Lookup coupon
    coupon = (await session.execute(
        select(Coupon).where(Coupon.code == code, Coupon.is_deleted == False)
    )).scalar_one_or_none()

    # Validation
    error = None
    if not coupon:
        error = "❌ Invalid coupon code." if lang == "en" else "❌ كود كوبون غير صالح."
    elif not coupon.is_active:
        error = "❌ This coupon is no longer active." if lang == "en" else "❌ هذا الكوبون غير نشط."
    elif coupon.expires_at and coupon.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        error = "❌ This coupon has expired." if lang == "en" else "❌ هذا الكوبون منتهي الصلاحية."
    elif coupon.max_uses > 0 and coupon.used_count >= coupon.max_uses:
        error = "❌ This coupon has reached its usage limit." if lang == "en" else "❌ تم استنفاد عدد مرات استخدام الكوبون."
    elif coupon.applies_to:
        allowed_products = coupon.applies_to.get("product_ids", [])
        allowed_categories = coupon.applies_to.get("category_ids", [])
        product = await _get_order_product(session, order)
        if product and allowed_products and str(product.id) not in allowed_products:
            error = "❌ This coupon doesn't apply to this product." if lang == "en" else "❌ هذا الكوبون لا ينطبق على هذا المنتج."
        elif product and allowed_categories and str(product.category_id) not in allowed_categories:
            error = "❌ This coupon doesn't apply to this category." if lang == "en" else "❌ هذا الكوبون لا ينطبق على فئة هذا المنتج."
    elif coupon.min_order > 0 and order.total_amount < coupon.min_order:
        min_txt = f"${coupon.min_order:.2f}"
        error = f"❌ Minimum order amount is {min_txt}." if lang == "en" else f"❌ الحد الأدنى للطلب {min_txt}."

    if error:
        osid = _sid(order_id)
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text="🔄 Try Again" if lang == "en" else "🔄 حاول مرة أخرى",
            callback_data=f"coupon:{osid}",
        ))
        builder.row(InlineKeyboardButton(
            text="⬅️ Back" if lang == "en" else "⬅️ رجوع",
            callback_data=f"skipcpn:{osid}",
        ))
        await message.answer(error, reply_markup=builder.as_markup())
        return

    # Calculate discount on total order amount
    total = order.total_amount
    if coupon.type == "percent":
        discount = round(total * coupon.value / 100, 2)
        if coupon.max_discount and discount > coupon.max_discount:
            discount = coupon.max_discount
        discount_label = f"{coupon.value:.0f}%"
    else:
        discount = round(min(coupon.value, total), 2)
        discount_label = f"${coupon.value:.2f}"

    final_amount = round(max(total - discount, 0), 2)

    # Update order with coupon
    order.discount_amount = discount
    order.final_amount = final_amount
    order.coupon_code = coupon.code
    coupon.used_count += 1
    await session.commit()

    # Get product info for display
    product = await _get_order_product(session, order)
    name = product.names_i18n.get(lang, product.name) if product and product.names_i18n else (product.name if product else "Product")
    emoji = (product.meta or {}).get("emoji", "📦") if product else "📦"

    # Get order items for qty
    oi_result = await session.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    order_items = oi_result.scalars().all()
    qty = sum(oi.quantity for oi in order_items)

    if lang == "ar":
        text = (
            f"🎟 <b>تم تطبيق الكوبون!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 الطلب: <b>{order.order_number}</b>\n"
            f"{emoji} <b>{name}</b> x{qty}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 المبلغ: <s>${total:.2f}</s>\n"
            f"🏷 الخصم ({discount_label}): -${discount:.2f}\n"
            f"✅ الإجمالي: <b>${final_amount:.2f}</b>\n"
            f"🎫 الكوبون: <code>{coupon.code}</code>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"💳 اضغط <b>ادفع الآن</b> للمتابعة"
        )
    else:
        text = (
            f"🎟 <b>Coupon Applied!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 Order: <b>{order.order_number}</b>\n"
            f"{emoji} <b>{name}</b> x{qty}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 Subtotal: <s>${total:.2f}</s>\n"
            f"🏷 Discount ({discount_label}): -${discount:.2f}\n"
            f"✅ Total: <b>${final_amount:.2f}</b>\n"
            f"🎫 Coupon: <code>{coupon.code}</code>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"💳 Tap <b>Pay Now</b> to proceed"
        )

    # Show Pay Now button (no coupon button since already applied)
    osid = _sid(order_id)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="💳 Pay Now" if lang == "en" else "💳 ادفع الآن",
        callback_data=f"gopay:{osid}",
    ))
    builder.row(InlineKeyboardButton(
        text="❌ Cancel" if lang == "en" else "❌ إلغاء",
        callback_data=f"cancel_order:{osid}",
    ))
    await message.answer(text, reply_markup=builder.as_markup())


async def _create_order(event, session: AsyncSession, product_id: str, qty: int, lang: str,
                        coupon_code: str = None, api_email: str = None, api_emails: list = None):
    product = (await session.execute(select(Product).where(Product.id == product_id))).scalar_one_or_none()
    if not product:
        if isinstance(event, CallbackQuery):
            await event.answer("Product not found", show_alert=True)
        else:
            await event.answer("Product not found")
        return

    is_api = (product.meta or {}).get("delivery_type") == "api"

    if not is_api:
        # Normal stock check
        stock_count = (await session.execute(
            select(func.count(StockItem.id))
            .where(StockItem.product_id == product.id, StockItem.is_sold == False, StockItem.is_deleted == False)
        )).scalar() or 0
        if product.force_out_of_stock:
            stock_count = 0
        if stock_count < qty:
            msg = f"Not enough stock. Available: {stock_count}" if lang == "en" else f"المخزون غير كافي. المتوفر: {stock_count}"
            if isinstance(event, CallbackQuery):
                await event.answer(msg, show_alert=True)
            else:
                await event.answer(msg)
            return
    else:
        # API products: check force_out_of_stock only
        if product.force_out_of_stock:
            msg = "This product is currently unavailable." if lang == "en" else "هذا المنتج غير متاح حالياً."
            if isinstance(event, CallbackQuery):
                await event.answer(msg, show_alert=True)
            else:
                await event.answer(msg)
            return

    price = (await session.execute(
        select(ProductPrice).where(ProductPrice.product_id == product.id, ProductPrice.is_deleted == False).limit(1)
    )).scalar_one_or_none()
    if not price:
        if isinstance(event, CallbackQuery):
            await event.answer("No price set", show_alert=True)
        else:
            await event.answer("No price set")
        return

    total = round(price.price * qty, 2)
    tg_id = event.from_user.id
    user = (await session.execute(select(User).where(User.telegram_id == tg_id))).scalar_one_or_none()
    if not user:
        # Try string comparison
        user = (await session.execute(select(User).where(User.telegram_id == str(tg_id)))).scalar_one_or_none()
    if not user:
        # Auto-create user if not found
        from models.user import User as UserModel
        user = UserModel(telegram_id=tg_id, first_name=getattr(event.from_user, 'first_name', 'User') or 'User')
        session.add(user)
        await session.flush()
    order_number = _short_order_id()
    # Merge single email and multiple emails into delivery_data
    all_emails = api_emails or ([api_email] if api_email else [])
    delivery_data = {"emails": all_emails, "input_email": all_emails[0] if all_emails else ""} if all_emails else None
    order = Order(
        user_id=user.id, order_number=order_number,
        total_amount=total, discount_amount=0, final_amount=total,
        currency="USD", status="waiting_payment",
        delivery_data=delivery_data,
    )
    session.add(order)
    await session.flush()

    session.add(OrderItem(
        order_id=order.id, product_id=product.id,
        quantity=qty, unit_price=price.price, total_price=total, status="pending",
    ))

    if not is_api:
        # Reserve stock items for normal products
        stock_result = await session.execute(
            select(StockItem)
            .where(StockItem.product_id == product.id, StockItem.is_sold == False, StockItem.is_deleted == False)
            .limit(qty)
        )
        for item in stock_result.scalars().all():
            item.is_reserved = True
            item.order_id = order.id

    await session.commit()

    await _show_order_summary(event, session, order, lang)


async def _show_order_summary(event, session: AsyncSession, order, lang: str):
    """Show order details with Use Coupon / Pay buttons"""
    product = await _get_order_product(session, order)
    name = product.names_i18n.get(lang, product.name) if product and product.names_i18n else (product.name if product else "Product")
    desc = product.descriptions_i18n.get(lang, product.description) if product and product.descriptions_i18n else (product.description or "")
    meta = (product.meta or {}) if product else {}
    emoji = meta.get("emoji", "📦")
    custom_emoji_id = meta.get("custom_emoji_id")

    # Premium emoji for text
    if custom_emoji_id:
        emoji_display = f'<tg-emoji emoji-id="{custom_emoji_id}">{emoji}</tg-emoji>'
    else:
        emoji_display = emoji

    oi_result = await session.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    order_items = oi_result.scalars().all()
    qty = sum(oi.quantity for oi in order_items)
    unit_price = order_items[0].unit_price if order_items else 0

    desc_line = f"📝 <b>{'الوصف' if lang == 'ar' else 'Description'}:</b> {desc}\n" if desc else ""

    text = await cms.render(session, "order_summary", lang,
                            emoji=emoji_display,
                            product_name=name,
                            description=desc_line,
                            unit_price=f"{unit_price:.2f}",
                            qty=qty,
                            total_usd=f"{order.final_amount:.2f}",
                            order_number=order.order_number)

    kb = order_summary_kb(str(order.id), lang)

    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        try:
            await msg.edit_text(text, reply_markup=kb)
        except Exception:
            await msg.answer(text, reply_markup=kb)
        await event.answer()
    else:
        await msg.answer(text, reply_markup=kb)


async def _show_payment_methods(event, session: AsyncSession, order, lang: str):
    """Show payment method selection"""
    methods = (await session.execute(
        select(PaymentMethod).where(PaymentMethod.is_enabled == True, PaymentMethod.is_deleted == False)
        .order_by(PaymentMethod.sort_order)
    )).scalars().all()

    product = await _get_order_product(session, order)
    name = product.names_i18n.get(lang, product.name) if product and product.names_i18n else (product.name if product else "Product")
    emoji = (product.meta or {}).get("emoji", "📦") if product else "📦"

    oi_result = await session.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    order_items = oi_result.scalars().all()
    qty = sum(oi.quantity for oi in order_items)

    if lang == "ar":
        text = (
            f"💳 <b>اختر طريقة الدفع</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"{emoji} {name} x{qty}\n"
            f"💰 الإجمالي: <b>${order.final_amount:.2f}</b>\n"
            f"🆔 الطلب: <code>{order.order_number}</code>\n"
        )
    else:
        text = (
            f"💳 <b>Choose Payment Method</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"{emoji} {name} x{qty}\n"
            f"💰 Total: <b>${order.final_amount:.2f}</b>\n"
            f"🆔 Order: <code>{order.order_number}</code>\n"
        )

    if order.coupon_code:
        text += f"🎫 Coupon: <code>{order.coupon_code}</code>\n" if lang == "en" else f"🎫 الكوبون: <code>{order.coupon_code}</code>\n"
        if order.discount_amount > 0:
            text += f"🏷 Discount: -${order.discount_amount:.2f}\n" if lang == "en" else f"🏷 الخصم: -${order.discount_amount:.2f}\n"

    kb = payment_methods_kb(methods, order.id, order.final_amount, order.final_amount, lang, product_id=None)

    msg = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        try:
            await msg.edit_text(text, reply_markup=kb)
        except Exception:
            await msg.answer(text, reply_markup=kb)
        await event.answer()
    else:
        await msg.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("pay:"))
async def handle_payment(callback: CallbackQuery, session: AsyncSession, lang: str = "en"):
    parts = callback.data.split(":")
    order_id, method_code = parts[1], parts[2]

    order = (await session.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order:
        await callback.answer("Order not found", show_alert=True)
        return

    user = (await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )).scalar_one_or_none()

    if method_code == "wallet":
        wallet = (await session.execute(select(Wallet).where(Wallet.user_id == user.id))).scalar_one_or_none()
        if not wallet or wallet.balance < order.final_amount:
            await callback.answer("Insufficient balance" if lang == "en" else "رصيد غير كافي", show_alert=True)
            return

        wallet.balance -= order.final_amount
        wallet.total_spent += order.final_amount

        session.add(WalletTransaction(
            wallet_id=wallet.id, type="purchase", amount=-order.final_amount,
            balance_before=wallet.balance + order.final_amount,
            balance_after=wallet.balance,
            description=f"Order {order.order_number}", reference_id=str(order.id),
        ))

        order.status = "paid"
        order.payment_method = "wallet"
        user.total_spent += order.final_amount
        user.total_orders += 1

        session.add(Payment(
            order_id=order.id, user_id=user.id, method_code="wallet",
            amount=order.final_amount, currency="USD", status="confirmed",
            verification_type="auto",
        ))
        await session.commit()

        # ── Admin notify ──
        product = await _get_order_product(session, order)
        pname = product.name if product else "Unknown"
        await admin_notify.order_paid(callback.from_user, pname, order.final_amount, "wallet")

        await auto_deliver(callback, session, order, lang)

    else:
        method = (await session.execute(
            select(PaymentMethod).where(PaymentMethod.code == method_code)
        )).scalar_one_or_none()

        if not method:
            await callback.answer("Payment method not found", show_alert=True)
            return

        session.add(Payment(
            order_id=order.id, user_id=user.id, method_code=method_code,
            amount=order.final_amount, currency="USD", status="pending",
            verification_type="note", tx_note=order.order_number,
        ))
        order.payment_method = method_code
        await session.commit()

        wallet_addr = method.wallet_address or "Contact admin"
        timeout = settings.PAYMENT_TIMEOUT_MINUTES

        # Select CMS template based on method
        if "binance" in method_code.lower():
            template_key = "payment_binance"
        else:
            template_key = "payment_crypto"

        text = await cms.render(session, template_key, lang,
                                order_number=order.order_number,
                                wallet_address=wallet_addr,
                                amount=f"{order.final_amount:.2f}",
                                timeout=timeout)

        await callback.message.edit_text(text, reply_markup=payment_cancel_kb(order.id, lang))

    await callback.answer()


@router.callback_query(F.data.startswith("paid:"))
async def handle_paid_claim(callback: CallbackQuery, session: AsyncSession, lang: str = "en"):
    order_id = callback.data.split(":")[1]
    order = (await session.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if not order:
        await callback.answer("Order not found", show_alert=True)
        return

    # For Binance payments — instant verification by order ID
    if order.payment_method in ("binance_uid", "binance_pay"):
        await callback.answer("🔍 Checking payment..." if lang == "en" else "🔍 جاري التحقق...", show_alert=False)

        from dotenv import load_dotenv
        import os as _os, asyncio as _aio
        _bot_dir = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
        load_dotenv(_os.path.join(_bot_dir, ".env"))
        b_key = _os.environ.get("BINANCE_API_KEY", "")
        b_secret = _os.environ.get("BINANCE_API_SECRET", "")
        b_uid = _os.environ.get("BINANCE_UID", "")

        if not b_key or not b_secret:
            await callback.message.edit_text(
                "⚠️ Binance API not configured. Contact admin." if lang == "en"
                else "⚠️ API بينانس غير مُعد. تواصل مع الأدمن."
            )
            return

        from bot_services.binance_checker import BinanceChecker
        checker = BinanceChecker(b_key, b_secret, b_uid)
        await checker._sync_time()

        # Try twice: check now, wait 3s, check again
        found = False
        tx_id = ""
        for attempt in range(2):
            if attempt > 0:
                await _aio.sleep(3)  # small delay before retry

            transactions = await checker.get_pay_transactions()
            for tx in transactions:
                if checker._match_pay_transaction(tx, order.order_number, order.final_amount):
                    found = True
                    tx_id = str(tx.get("transactionId", tx.get("orderNo", "")))
                    break
            if found:
                break

        if found:
            # ✅ Payment found — confirm + deliver instantly
            payment = (await session.execute(
                select(Payment).where(Payment.order_id == order.id, Payment.status == "pending")
            )).scalar_one_or_none()
            if payment:
                payment.status = "confirmed"
                payment.tx_hash = tx_id
                payment.confirmed_at = datetime.now(timezone.utc).isoformat()

            order.status = "paid"
            user = (await session.execute(
                select(User).where(User.id == order.user_id)
            )).scalar_one_or_none()
            if user:
                user.total_spent += order.final_amount
                user.total_orders += 1
            await session.commit()

            # Auto deliver immediately
            await auto_deliver(callback, session, order, lang)
            return

        else:
            # ❌ Not found — show instructions with order ID
            oid = _sid(order.id)
            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(
                text="🔄 Check Again" if lang == "en" else "🔄 تحقق مرة أخرى",
                callback_data=f"paid:{order_id}",
            ))
            builder.row(InlineKeyboardButton(
                text="❌ Cancel order" if lang == "en" else "❌ إلغاء الطلب",
                callback_data=f"cancel_order:{oid}",
            ))

            text = (
                f"⏳ <b>Payment Not Detected Yet</b>\n\n"
                f"🆔 Order: <b>{order.order_number}</b>\n"
                f"💰 Amount: <b>${order.final_amount:.2f} USDT</b>\n\n"
                f"📌 <b>How to pay:</b>\n"
                f"1️⃣ Open Binance → Pay → Send\n"
                f"2️⃣ Enter UID: <code>{b_uid}</code>\n"
                f"3️⃣ Enter amount: <code>{order.final_amount:.2f}</code>\n"
                f"4️⃣ In the <b>Note</b> field, write:\n"
                f"    <code>{order.order_number}</code>\n\n"
                f"⏰ After sending, tap <b>Check Again</b>"
            ) if lang == "en" else (
                f"⏳ <b>لم يتم اكتشاف الدفع بعد</b>\n\n"
                f"🆔 الطلب: <b>{order.order_number}</b>\n"
                f"💰 المبلغ: <b>${order.final_amount:.2f} USDT</b>\n\n"
                f"📌 <b>طريقة الدفع:</b>\n"
                f"1️⃣ افتح بينانس → Pay → إرسال\n"
                f"2️⃣ أدخل UID: <code>{b_uid}</code>\n"
                f"3️⃣ أدخل المبلغ: <code>{order.final_amount:.2f}</code>\n"
                f"4️⃣ في خانة <b>الملاحظة (Note)</b> اكتب:\n"
                f"    <code>{order.order_number}</code>\n\n"
                f"⏰ بعد الإرسال، اضغط <b>تحقق مرة أخرى</b>"
            )
            try:
                await callback.message.edit_text(text, reply_markup=builder.as_markup())
            except Exception:
                await callback.message.answer(text, reply_markup=builder.as_markup())
            return
    else:
        # Non-Binance payment — mark as under review
        order.status = "under_review"
        await session.commit()

        text = (
            f"⏳ <b>Payment Under Review</b>\n\n"
            f"🆔 Order: <b>{order.order_number}</b>\n\n"
            f"Your payment is being verified. You'll be notified once confirmed."
        ) if lang == "en" else (
            f"⏳ <b>الدفع قيد المراجعة</b>\n\n"
            f"🆔 الطلب: <b>{order.order_number}</b>\n\n"
            f"يتم التحقق من الدفع. سيتم إبلاغك عند التأكيد."
        )
        await callback.message.edit_text(text, reply_markup=back_kb("menu:back", lang))
        await callback.answer()


@router.callback_query(F.data.startswith("cancel_order:"))
async def cancel_order(callback: CallbackQuery, session: AsyncSession, lang: str = "en"):
    raw_id = callback.data.split(":")[1]
    order_id = _eid(raw_id) if '-' not in raw_id else raw_id
    order = (await session.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if order and order.status in ("waiting_payment", "pending"):
        order.status = "canceled"
        result = await session.execute(select(StockItem).where(StockItem.order_id == order.id))
        for item in result.scalars().all():
            item.is_reserved = False
            item.order_id = None
        await session.commit()

    text = "❌ Order canceled." if lang == "en" else "❌ تم إلغاء الطلب."
    await callback.message.edit_text(text, reply_markup=await main_menu_inline_kb(lang))
    await callback.answer()


async def auto_deliver(callback: CallbackQuery, session: AsyncSession, order, lang: str = "en"):
    """Deliver order — stock items for normal products, API call for API products"""
    from aiogram.types import BufferedInputFile

    product = await _get_order_product(session, order)
    is_api = product and (product.meta or {}).get("delivery_type") == "api"

    if is_api:
        await _api_deliver(callback, session, order, product, lang)
        return

    # ── Normal stock delivery ──
    result = await session.execute(
        select(StockItem).where(StockItem.order_id == order.id, StockItem.is_reserved == True)
    )
    items = result.scalars().all()

    delivery_data = []
    for item in items:
        item.is_sold = True
        item.is_reserved = False
        item.sold_to = order.user_id
        delivery_data.append(item.data)

    oi_result = await session.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    for oi in oi_result.scalars().all():
        oi.status = "delivered"
        oi.delivered_data = "\n".join(delivery_data)

    order.status = "delivered"
    order.delivery_data = {"items": delivery_data}
    await session.commit()

    # ── Auto-credit referral commission ──
    await credit_referral_commission(session, order.user_id, order.final_amount)

    # ── Build delivery info ──
    meta = product.meta or {} if product else {}
    name = (product.names_i18n.get(lang, product.name) if product and product.names_i18n else product.name) if product else "Product"
    note_raw = meta.get(f"delivery_note_{lang}") or meta.get("delivery_note_en", "")
    now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S")
    qty = len(delivery_data)

    # Build note line — only show if set
    note_line = f"⚠️ <b>Note:</b> {note_raw}" if note_raw else ""

    # ── MESSAGE 1: CMS-rendered text ──
    items_text = "\n".join([f"<code>{d}</code>" for d in delivery_data])

    msg1 = await cms.render(session, "order_delivered", lang,
                            product_name=name,
                            order_number=order.order_number,
                            purchase_date=now_str,
                            note=note_line,
                            delivery_items=items_text,
                            qty=qty)

    try:
        await callback.message.edit_text(msg1)
    except Exception:
        await callback.message.answer(msg1)

    # ── MESSAGE 2: CMS-rendered caption + txt file ──
    txt_content = (
        f"=== DELIVERY RECEIPT ===\n"
        f"Product: {name}\n"
        f"Order ID: {order.order_number}\n"
        f"Purchase date: {now_str}\n"
        f"Quantity: {qty}\n"
        f"{'=' * 30}\n\n"
    )
    for i, d in enumerate(delivery_data, 1):
        txt_content += f"  {i}. {d}\n"
    if note_raw:
        txt_content += f"\nNote: {note_raw}\n"

    safe_name = (product.name if product else "order").replace(" ", "_").replace("/", "-")[:30]
    file_name = f"{safe_name}_{order.order_number}_{datetime.now().strftime('%d_%m_%Y_%H_%M_%S')}.txt"

    doc_file = BufferedInputFile(
        txt_content.encode("utf-8"),
        filename=file_name,
    )

    doc_caption = await cms.render(session, "delivery_file_caption", lang,
                                   product_name=name,
                                   order_number=order.order_number,
                                   purchase_date=now_str,
                                   note=note_line,
                                   delivery_items=items_text,
                                   qty=qty)

    await callback.message.answer_document(
        document=doc_file,
        caption=doc_caption,
    )



async def _api_deliver(callback: CallbackQuery, session: AsyncSession, order, product, lang: str):
    """Call external API for product activation — supports multiple emails"""
    import logging as _log
    _logger = _log.getLogger(__name__)
    from bot_services.api_delivery import call_api

    meta       = product.meta or {}
    # Merge top-level meta + nested api_config so credentials work either way
    api_config = {**meta, **(meta.get("api_config") or {})}
    api_config["provider_product_code"] = product.provider_product_code
    ddata      = order.delivery_data or {}
    emails     = ddata.get("emails") or ([ddata["input_email"]] if ddata.get("input_email") else [])
    email_display = emails[0] if len(emails) == 1 else f"{len(emails)} emails"

    proc_msg = (
        f"⏳ <b>Activating your subscription...</b>\n\n"
        f"📧 {email_display}\n\n"
        "Please wait a moment."
    ) if lang == "en" else (
        f"⏳ <b>جاري تفعيل اشتراكك...</b>\n\n"
        f"📧 {email_display}\n\n"
        "انتظر لحظة."
    )
    try:
        await callback.message.edit_text(proc_msg)
    except Exception:
        pass

    # Call Adobe API for each email
    results = []
    for em in emails:
        r = await call_api(api_config, em, order.order_number, qty=1)
        _logger.info("[_api_deliver] email=%s result=%s", em, r)
        results.append((em, r))

    all_success = all(r["success"] for _, r in results)
    combined_msg = "\n".join(
        f"{'✅' if r['success'] else '❌'} {em}: {r.get('message', r.get('error', ''))}"
        for em, r in results
    )

    # Update order items
    oi_result = await session.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    for oi in oi_result.scalars().all():
        oi.status = "delivered" if all_success else "failed"
        oi.delivered_data = combined_msg

    if all_success:
        order.status = "delivered"
        order.delivery_data = {
            "emails": emails,
            "input_email": emails[0] if emails else "",
            "api_result": [r.get("data") for _, r in results],
            "activation_message": combined_msg,
        }
        await session.commit()

        # ── Auto-credit referral commission ──
        await credit_referral_commission(session, order.user_id, order.final_amount)

        name = product.names_i18n.get(lang, product.name) if product.names_i18n else product.name
        emoji = meta.get("emoji", "✅")
        emails_display = "\n".join(f"📧 <code>{e}</code>" for e in emails)

        if lang == "ar":
            text = (
                f"✅ <b>تم تفعيل اشتراكك!</b>\n\n"
                f"{emoji} <b>{name}</b>\n\n"
                f"📬 <b>البريدات ({len(emails)}):</b>\n{emails_display}\n\n"
                f"📋 <b>نتيجة التفعيل:</b>\n{combined_msg}\n\n"
                f"🆔 الطلب: <code>{order.order_number}</code>\n\n"
                "شكراً لشرائك! 🎉"
            )
        else:
            text = (
                f"✅ <b>Subscription Activated!</b>\n\n"
                f"{emoji} <b>{name}</b>\n\n"
                f"📬 <b>Emails ({len(emails)}):</b>\n{emails_display}\n\n"
                f"📋 <b>Activation Result:</b>\n{combined_msg}\n\n"
                f"🆔 Order: <code>{order.order_number}</code>\n\n"
                "Thank you for your purchase! 🎉"
            )
        await callback.message.edit_text(text)

    else:
        order.status = "paid"
        order.delivery_data = {
            "emails": emails,
            "input_email": emails[0] if emails else "",
            "api_error": combined_msg,
        }
        await session.commit()

        err = combined_msg or "Unknown error"
        emails_display = "\n".join(f"📧 <code>{e}</code>" for e in emails)
        if lang == "ar":
            text = (
                f"⚠️ <b>فشل التفعيل التلقائي</b>\n\n"
                f"📬 البريدات:\n{emails_display}\n"
                f"🆔 الطلب: <code>{order.order_number}</code>\n\n"
                f"❌ السبب:\n{err}\n\n"
                "تم حفظ طلبك. سيتواصل معك الدعم في أقرب وقت."
            )
        else:
            text = (
                f"⚠️ <b>Auto-Activation Failed</b>\n\n"
                f"📬 Emails:\n{emails_display}\n"
                f"🆔 Order: <code>{order.order_number}</code>\n\n"
                f"❌ Error:\n{err}\n\n"
                "Your order is saved. Support will contact you shortly."
            )
        await callback.message.edit_text(text)
