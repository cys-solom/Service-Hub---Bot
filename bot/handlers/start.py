"""Start handler — welcome, language, main menu — ALL text from CMS templates"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
from models.user import User
from models.wallet import Wallet
from models.referral import Referral

from config import settings
from keyboards import (
    language_kb, main_menu_inline_kb, main_menu_reply_kb, back_kb,
)
from bot_services import cms
from bot_services.store_settings import get_store_vars, get_setting
from bot_services import admin_notify
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()


async def get_or_create_user(session: AsyncSession, tg_user, referrer_id=None):
    from bot_services.store_settings import get_setting
    result = await session.execute(select(User).where(User.telegram_id == tg_user.id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
            language_code=tg_user.language_code or "en",
        )
        session.add(user)
        await session.flush()

        wallet = Wallet(user_id=user.id, balance=0, currency=settings.DEFAULT_CURRENCY)
        session.add(wallet)

        # Referral — only if system is enabled
        if referrer_id:
            try:
                ref_enabled = (await get_setting(session, "referral_enabled", "true")) == "true"
                if ref_enabled:
                    ref_user = (await session.execute(
                        select(User).where(User.telegram_id == int(referrer_id))
                    )).scalar_one_or_none()
                    if ref_user and ref_user.id != user.id:
                        # Check max invites
                        max_invites = int(await get_setting(session, "referral_max_invites", "0"))
                        if max_invites > 0:
                            current_count = (await session.execute(
                                select(func.count(Referral.id)).where(Referral.referrer_id == ref_user.id)
                            )).scalar() or 0
                            if current_count >= max_invites:
                                ref_user = None  # skip — max reached
                        if ref_user:
                            commission = float(await get_setting(session, "referral_commission_percent", "5"))
                            referral = Referral(
                                referrer_id=ref_user.id,
                                referred_id=user.id,
                                commission_percent=commission,
                            )
                            session.add(referral)
                            user.referred_by_id = str(ref_user.telegram_id)
            except (ValueError, Exception):
                pass

        await session.commit()
        user._is_new = True  # flag for notification
    else:
        user.username = tg_user.username
        user.first_name = tg_user.first_name
        user.last_name = tg_user.last_name
        await session.commit()

    return user


async def _safe_send(target, text, **kwargs):
    """Send message with HTML, fall back to plain text if HTML is invalid"""
    # Clean broken HTML: remove unclosed tags at end
    last_open = text.rfind('<')
    last_close = text.rfind('>')
    if last_open > last_close:
        text = text[:last_open].rstrip()

    try:
        if isinstance(target, CallbackQuery):
            return await target.message.edit_text(text, **kwargs)
        else:
            return await target.answer(text, **kwargs)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"HTML send failed: {e}")
        # Strip ALL HTML tags for plain text fallback
        import re
        plain = re.sub(r'<[^>]+>', '', text)
        kwargs.pop("parse_mode", None)
        kwargs["parse_mode"] = None
        try:
            if isinstance(target, CallbackQuery):
                return await target.message.edit_text(plain, **kwargs)
            else:
                return await target.answer(plain, **kwargs)
        except Exception:
            pass


async def _get_menu_text(session, lang, bot_username):
    """Get main menu text from CMS template — reads store settings from DB"""
    sv = await get_store_vars(session, settings)
    text = await cms.render(session, "main_menu", lang,
        bot_username=bot_username,
        **sv,
    )
    return text


async def _get_welcome_text(session, lang, ref_link):
    """Get welcome text from CMS template"""
    text = await cms.render(session, "welcome", lang,
        store_name=settings.STORE_NAME,
        ref_link=ref_link,
    )
    return text


async def _check_force_join(bot, session, user_id: int, lang: str):
    """
    Check if user must join channel and/or group.
    Returns: (all_joined: bool, missing: list[{type, url, chat_id}])
    """
    missing = []

    # Check channel
    ch_enabled = await get_setting(session, "force_channel_enabled", "false")
    if ch_enabled == "true":
        ch_url = await get_setting(session, "force_channel_url", "")
        ch_id = await get_setting(session, "force_channel_chat_id", "")
        if ch_url and ch_id:
            try:
                member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
                if member.status not in ("member", "administrator", "creator"):
                    missing.append({"type": "channel", "url": ch_url, "chat_id": ch_id})
            except Exception:
                missing.append({"type": "channel", "url": ch_url, "chat_id": ch_id})

    # Check group
    gr_enabled = await get_setting(session, "force_group_enabled", "false")
    if gr_enabled == "true":
        gr_url = await get_setting(session, "force_group_url", "")
        gr_id = await get_setting(session, "force_group_chat_id", "")
        if gr_url and gr_id:
            try:
                member = await bot.get_chat_member(chat_id=gr_id, user_id=user_id)
                if member.status not in ("member", "administrator", "creator"):
                    missing.append({"type": "group", "url": gr_url, "chat_id": gr_id})
            except Exception:
                missing.append({"type": "group", "url": gr_url, "chat_id": gr_id})

    return len(missing) == 0, missing


def _force_join_kb(missing: list, lang: str):
    """Keyboard with join buttons for each missing channel/group + verify"""
    builder = InlineKeyboardBuilder()
    for m in missing:
        if m["type"] == "channel":
            txt = "📣 انضم للقناة" if lang == "ar" else "📣 Join Channel"
        else:
            txt = "👥 انضم للمجموعة" if lang == "ar" else "👥 Join Group"
        builder.row(InlineKeyboardButton(text=txt, url=m["url"]))

    builder.row(InlineKeyboardButton(
        text="✅ تحقق من الاشتراك" if lang == "ar" else "✅ Verify Membership",
        callback_data="force_join:check"
    ))
    return builder.as_markup()


# ─── /start ──────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext, lang: str = "en", **kwargs):
    await state.clear()

    referrer_id = None
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref"):
        referrer_id = args[1][3:]

    user = await get_or_create_user(session, message.from_user, referrer_id)

    # ── Notify admin (ALWAYS — before force join check) ──
    if hasattr(user, '_is_new') and user._is_new:
        await admin_notify.new_user(message.from_user)
    else:
        await admin_notify.user_started(message.from_user)

    # ── Force join check ──
    all_joined, missing = await _check_force_join(message.bot, session, message.from_user.id, lang)
    if not all_joined:
        parts = []
        for m in missing:
            if m["type"] == "channel":
                parts.append("📣 القناة" if lang == "ar" else "📣 Channel")
            else:
                parts.append("👥 المجموعة" if lang == "ar" else "👥 Group")
        join_list = " + ".join(parts)

        if lang == "ar":
            text = (
                "━━━━━━━━━━━━━━━━━━\n"
                "📢  <b>انضم أولاً!</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"يجب عليك الانضمام لـ {join_list} أولاً.\n\n"
                "✅ بعد الانضمام، اضغط <b>تحقق من الاشتراك</b>"
            )
        else:
            text = (
                "━━━━━━━━━━━━━━━━━━\n"
                "📢  <b>Join Required!</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"You must join {join_list} before using this bot.\n\n"
                "✅ After joining, tap <b>Verify Membership</b>"
            )
        await message.answer(text, reply_markup=_force_join_kb(missing, lang))
        return

    bot_info = await message.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref{message.from_user.id}"

    text = await _get_welcome_text(session, lang, ref_link)

    await _safe_send(message, text, reply_markup=language_kb())
    await message.answer("👇 Choose your language:", reply_markup=await main_menu_reply_kb(lang))


# ─── Force Join: Check Membership ────────────────────
@router.callback_query(F.data == "force_join:check")
async def cb_force_join_check(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str = "en", **kwargs):
    all_joined, missing = await _check_force_join(callback.bot, session, callback.from_user.id, lang)

    if all_joined:
        if lang == "ar":
            await callback.answer("✅ تم التحقق! مرحباً بك", show_alert=True)
        else:
            await callback.answer("✅ Verified! Welcome", show_alert=True)

        # Show the menu
        await state.clear()
        await get_or_create_user(session, callback.from_user)
        bot_info = await callback.bot.get_me()
        text = await _get_menu_text(session, lang, bot_info.username)
        sv = await get_store_vars(session, settings)
        try:
            await callback.message.edit_text(text,
                reply_markup=await main_menu_inline_kb(lang, sv["channel_url"], sv["support_user"]))
        except Exception:
            pass
    else:
        names = []
        for m in missing:
            names.append("القناة" if m["type"] == "channel" else "المجموعة") if lang == "ar" else names.append("Channel" if m["type"] == "channel" else "Group")
        still = " + ".join(names)
        if lang == "ar":
            await callback.answer(f"❌ لم تنضم لـ {still} بعد!", show_alert=True)
        else:
            await callback.answer(f"❌ Not joined {still} yet!", show_alert=True)


# ─── /menu ───────────────────────────────────────────
@router.message(Command("menu"))
async def cmd_menu(message: Message, session: AsyncSession, state: FSMContext, lang: str = "en", **kwargs):
    await state.clear()
    await get_or_create_user(session, message.from_user)
    bot_info = await message.bot.get_me()

    text = await _get_menu_text(session, lang, bot_info.username)

    sv = await get_store_vars(session, settings)
    await _safe_send(message, text,
        reply_markup=await main_menu_inline_kb(lang, sv["channel_url"], sv["support_user"]))


# ─── Back to menu ────────────────────────────────────
@router.callback_query(F.data == "menu:back")
async def cb_back_to_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str = "en", **kwargs):
    await state.clear()
    await get_or_create_user(session, callback.from_user)
    bot_info = await callback.bot.get_me()

    text = await _get_menu_text(session, lang, bot_info.username)

    sv = await get_store_vars(session, settings)
    try:
        await callback.message.edit_text(text,
            reply_markup=await main_menu_inline_kb(lang, sv["channel_url"], sv["support_user"]))
    except Exception:
        await callback.message.edit_text(text,
            reply_markup=await main_menu_inline_kb(lang, sv["channel_url"], sv["support_user"]),
            parse_mode=None)
    await callback.answer()


# ─── Reply keyboard handlers ────────────────────────
@router.message(F.text.in_(["🛍 Shop", "🛍 المتجر", "🛍 SHOP"]))
async def reply_shop(message: Message, session: AsyncSession, state: FSMContext, lang: str = "en", **kwargs):
    await state.clear()
    from handlers.catalog import show_products_list
    await show_products_list(message, session, lang)


@router.message(F.text.in_(["📋 Menu", "📋 القائمة", "📋 MENU"]))
async def reply_menu(message: Message, session: AsyncSession, state: FSMContext, lang: str = "en", **kwargs):
    await state.clear()
    await get_or_create_user(session, message.from_user)
    bot_info = await message.bot.get_me()
    text = await _get_menu_text(session, lang, bot_info.username)
    sv = await get_store_vars(session, settings)
    await _safe_send(message, text,
        reply_markup=await main_menu_inline_kb(lang, sv["channel_url"], sv["support_user"]))


@router.message(F.text.in_(["💰 Wallet", "💰 المحفظة", "💰 WALLET"]))
async def reply_wallet(message: Message, session: AsyncSession, state: FSMContext, lang: str = "en", **kwargs):
    await state.clear()
    from handlers.wallet import show_wallet
    await show_wallet(message, session, lang)


@router.message(F.text.in_(["🏦 Top up", "🏦 شحن", "🏦 TOP UP"]))
async def reply_topup(message: Message, session: AsyncSession, state: FSMContext, lang: str = "en", **kwargs):
    await state.clear()
    from handlers.wallet import show_deposit
    await show_deposit(message, session, lang)


@router.message(F.text.in_(["📦 Order history", "📦 سجل الطلبات", "📦 ORDERS"]))
async def reply_orders(message: Message, session: AsyncSession, state: FSMContext, lang: str = "en", **kwargs):
    await state.clear()
    from handlers.orders import show_orders
    await show_orders(message, session, lang)




# ─── Referral ────────────────────────────────────────
@router.message(Command("ref"))
@router.callback_query(F.data == "menu:referral")
async def show_referral(event, session: AsyncSession, lang: str = "en", **kwargs):
    from bot_services.store_settings import get_setting
    tg_user = event.from_user
    user = (await session.execute(
        select(User).where(User.telegram_id == tg_user.id)
    )).scalar_one_or_none()

    # Check if referral system is enabled
    ref_enabled = (await get_setting(session, "referral_enabled", "true")) == "true"
    if not ref_enabled:
        text = "⚠️ <b>Referral program is currently disabled.</b>" if lang == "en" else "⚠️ <b>برنامج الإحالة معطل حالياً.</b>"
        if isinstance(event, CallbackQuery):
            try:
                await event.message.edit_text(text, reply_markup=back_kb("menu:back", lang))
            except Exception:
                await event.message.answer(text, reply_markup=back_kb("menu:back", lang))
            await event.answer()
        else:
            await event.answer(text, reply_markup=back_kb("menu:back", lang))
        return

    commission = float(await get_setting(session, "referral_commission_percent", "5"))
    bot_info = await event.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref{tg_user.id}"

    ref_count = (await session.execute(
        select(func.count(Referral.id)).where(Referral.referrer_id == user.id, Referral.is_deleted == False)
    )).scalar() or 0

    total_earned = (await session.execute(
        select(func.coalesce(func.sum(Referral.total_earned), 0))
        .where(Referral.referrer_id == user.id, Referral.is_deleted == False)
    )).scalar() or 0

    if lang == "ar":
        text = (
            f"👥 <b>برنامج الإحالة</b>\n\n"
            f"🔗 رابطك:\n<code>{ref_link}</code>\n\n"
            f"👥 عدد الدعوات: <b>{ref_count}</b>\n"
            f"💰 العمولة: <b>{commission}%</b>\n"
            f"💵 إجمالي الأرباح: <b>${float(total_earned):.2f}</b>\n\n"
            f"شارك رابطك واربح!"
        )
    else:
        text = (
            f"👥 <b>Referral Program</b>\n\n"
            f"🔗 Your link:\n<code>{ref_link}</code>\n\n"
            f"👥 Total referrals: <b>{ref_count}</b>\n"
            f"💰 Commission: <b>{commission}%</b>\n"
            f"💵 Total earned: <b>${float(total_earned):.2f}</b>\n\n"
            f"Share your link and earn!"
        )

    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=back_kb("menu:back", lang))
        except Exception:
            await event.message.answer(text, reply_markup=back_kb("menu:back", lang))
        await event.answer()
    else:
        await event.answer(text, reply_markup=back_kb("menu:back", lang))


# ─── Support / API Key stubs ─────────────────────────
@router.message(Command("apikey"))
@router.callback_query(F.data == "menu:apikey")
async def show_apikey(event, lang: str = "en", **kwargs):
    text = "🔑 <b>Stock API Key</b>\n\n🚧 Coming soon!"
    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=back_kb("menu:back", lang))
        except Exception:
            pass
        await event.answer()
    else:
        await event.answer(text, reply_markup=back_kb("menu:back", lang))


@router.callback_query(F.data == "menu:support")
async def show_support(callback: CallbackQuery, session: AsyncSession, lang: str = "en", **kwargs):
    sv = await get_store_vars(session, settings)
    text = f"💬 <b>Support</b>\n\nContact admin: {sv['support_user']}"
    try:
        await callback.message.edit_text(text, reply_markup=back_kb("menu:back", lang))
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "menu:topup")
async def cb_topup(callback: CallbackQuery, session: AsyncSession, lang: str = "en", **kwargs):
    from handlers.wallet import show_deposit
    await show_deposit(callback, session, lang)
