# -*- coding: utf-8 -*-
"""CMS Editor v4 — Clean & Professional /editmsg"""
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

import sys, os, re, logging, html as _html
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
from models.cms import MessageTemplate
from models.catalog import Product

from config import settings
from bot_services import cms

router = Router()
logger = logging.getLogger(__name__)

BACK_TEXT = "\u2b05\ufe0f Back"
BACK_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=BACK_TEXT)]],
    resize_keyboard=True, one_time_keyboard=True,
)

PAGE_TEMPLATES = {
    "welcome":                "\U0001f3e0 Welcome",
    "main_menu":              "\U0001f4cb Main Menu",
    "product_list_header":    "\U0001f4e6 Product List Header",
    "product_list_footer":    "\U0001f4e6 Product List Footer",
    "product_detail":         "\U0001f6cd Product Detail (default)",
    "order_summary":          "\U0001f9fe Order Summary",
    "payment_binance":        "\U0001f4ab Binance Payment",
    "payment_crypto":         "\U0001f48e Crypto Payment",
    "order_delivered":        "\u2705 Delivery Message (Text)",
    "delivery_file_caption":  "\U0001f4ce Delivery Message (File)",
    "payment_confirmed_auto": "\U0001f4b3 Payment Confirmed",
    "notify_deposit_approved":"\u2705 Deposit Approved",
    "notify_deposit_rejected":"\u274c Deposit Rejected",
    "notify_order_delivered": "\U0001f4e6 Notify: Order Delivered",
    "notify_order_rejected":  "\U0001f6ab Notify: Order Rejected",
    "notify_balance_deducted":"\U0001f4e4 Notify: Balance Deducted",
    "notify_admin_deposit":   "\U0001f4b0 Notify: Admin Deposit",
    "notify_stock_added":     "\u26a1 Notify: Stock Added",
    "notify_product_added":   "\U0001f4e6 Notify: New Product",
}


class Edit(StatesGroup):
    text_en = State()
    text_ar = State()
    btn_emoji = State()
    btn_en    = State()
    btn_ar    = State()
    note_en   = State()
    note_ar   = State()


def _admin(uid): return uid in settings.admin_ids_list

def _expand(s):
    h = s.strip()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"

def _short(uid): return str(uid).replace('-', '')

def _clean(t):
    t = re.sub(r'^<pre>(.*)</pre>$', r'\1', t, flags=re.DOTALL)
    t = re.sub(r'^<code>(.*)</code>$', r'\1', t, flags=re.DOTALL)
    lo, lc = t.rfind('<'), t.rfind('>')
    if lo > lc: t = t[:lo].rstrip()
    return t.strip()


def _extract_text(message) -> str | None:
    """
    The ONE function that captures everything:
    • Telegram bold/italic/code/spoiler  → from html_text entities
    • Premium custom emojis              → from html_text <tg-emoji> tags
    • Manually typed <b>HTML</b> tags    → html.unescape restores &lt;b&gt; → <b>
    """
    raw = None
    if message.text:
        raw = _html.unescape(message.html_text)   # ← the magic one-liner
    elif message.caption:
        raw = _html.unescape(message.caption_html)
    if raw:
        has_tg_emoji = "<tg-emoji" in raw
        logger.info(f"[CMS] _extract_text: len={len(raw)} has_tg_emoji={has_tg_emoji}")
        if has_tg_emoji:
            logger.info(f"[CMS] _extract_text RAW (first 500): {raw[:500]}")
    return _clean(raw) if raw else None

def _safe(t, n=280):
    s = (t or "").replace("<","&lt;").replace(">","&gt;")
    return s[:n] + ("…" if len(s)>n else "")


async def _save_tpl(session, key, en=None, ar=None):
    logger.info(f"[CMS-SAVE] key={key}, en_len={len(en) if en else 0}, ar_len={len(ar) if ar else 0}")
    # MUST match same filters as cms.get_template — otherwise we may update
    # a deleted copy while render reads the active one
    tpl = (await session.execute(
        select(MessageTemplate).where(
            MessageTemplate.key == key,
            MessageTemplate.is_active == True,
            MessageTemplate.is_deleted == False,
        )
    )).scalar_one_or_none()

    if not tpl:
        # Diagnostic: check if ANY template exists with this key
        any_count = (await session.execute(
            select(func.count(MessageTemplate.id)).where(MessageTemplate.key == key)
        )).scalar()
        logger.error(f"[CMS-SAVE] Template '{key}' NOT FOUND (active)! Total in DB: {any_count}")
        return False

    logger.info(f"[CMS-SAVE] Found template id={tpl.id}, current content_len={len(tpl.content or '')}")

    changed = False
    if en:
        old_len = len(tpl.content or '')
        tpl.content = en
        flag_modified(tpl, "content")
        changed = True
        logger.info(f"[CMS-SAVE] EN updated: {old_len} -> {len(en)} chars")
        if "<tg-emoji" in en:
            logger.info(f"[CMS-SAVE] EN contains <tg-emoji> tags ✓")
    else:
        logger.info(f"[CMS-SAVE] EN is None/empty — skipping")

    if ar:
        cur = dict(tpl.content_i18n) if isinstance(tpl.content_i18n, dict) else {}
        cur["ar"] = ar
        tpl.content_i18n = cur
        flag_modified(tpl, "content_i18n")
        changed = True
        logger.info(f"[CMS-SAVE] AR updated: {len(ar)} chars")
    else:
        logger.info(f"[CMS-SAVE] AR is None/empty — skipping")

    if not changed:
        logger.warning(f"[CMS-SAVE] Nothing to save (both en and ar are empty)")
        return True  # nothing to save is still "ok"

    try:
        await session.flush()
        await session.commit()
        logger.info(f"[CMS-SAVE] ✅ Committed successfully!")

        # Verify the save by re-reading with same active filters
        verify = (await session.execute(
            select(MessageTemplate).where(
                MessageTemplate.key == key,
                MessageTemplate.is_active == True,
                MessageTemplate.is_deleted == False,
            )
        )).scalar_one_or_none()
        if verify:
            saved_len = len(verify.content or '')
            logger.info(f"[CMS-SAVE] ✅ Verified: content_len={saved_len}")
            if en and saved_len != len(en):
                logger.error(f"[CMS-SAVE] ❌ MISMATCH! Expected {len(en)} but got {saved_len}")
        return True
    except Exception as e:
        logger.error(f"[CMS-SAVE] ❌ COMMIT FAILED: {e}", exc_info=True)
        await session.rollback()
        return False


# ── /cancel ──────────────────────────────────────────
@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, **kwargs):
    if await state.get_state():
        await state.clear()
        await message.answer("\u2705 Cancelled.", reply_markup=ReplyKeyboardRemove())


@router.message(F.text == BACK_TEXT)
async def back_text(message: Message, state: FSMContext, **kwargs):
    await state.clear()
    await message.answer("Cancelled. Use /editmsg.", reply_markup=ReplyKeyboardRemove())


# ── /editmsg ─────────────────────────────────────────
@router.message(Command("editmsg"))
async def cmd_editmsg(message: Message, state: FSMContext, **kwargs):
    if not _admin(message.from_user.id): return
    await state.clear()
    await _main_menu(message)


async def _main_menu(target):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="\U0001f6cd Products", callback_data="cme_products"))
    kb.row(InlineKeyboardButton(text="\U0001f4c4 Pages & Notifications", callback_data="cme_pages"))
    kb.row(InlineKeyboardButton(text="\u274c Close", callback_data="cme_close"))
    txt = "\u270f\ufe0f <b>Message Editor</b>\n\nWhat do you want to edit?"
    if isinstance(target, CallbackQuery):
        try: await target.message.edit_text(txt, reply_markup=kb.as_markup())
        except: await target.message.answer(txt, reply_markup=kb.as_markup())
    else:
        await target.answer(txt, reply_markup=kb.as_markup())


# ── Products list ─────────────────────────────────────
@router.callback_query(F.data == "cme_products")
async def cb_products(callback: CallbackQuery, session: AsyncSession, **kwargs):
    if not _admin(callback.from_user.id):
        return await callback.answer("Admin only", show_alert=True)
    products = (await session.execute(
        select(Product).where(Product.is_deleted==False).order_by(Product.sort_order)
    )).scalars().all()
    kb = InlineKeyboardBuilder()
    for p in products:
        emoji = (p.meta or {}).get("emoji", "\U0001f4e6")
        kb.row(InlineKeyboardButton(
            text=f"{emoji}  {p.name[:38]}",
            callback_data=f"cme_p:{_short(p.id)}",
        ))
    kb.row(InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="cme_main"))
    await callback.message.edit_text(
        "\U0001f6cd <b>Products</b>\n\nSelect a product to edit:",
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


# ── Product actions ───────────────────────────────────
@router.callback_query(F.data.startswith("cme_p:"))
async def cb_product(callback: CallbackQuery, session: AsyncSession, **kwargs):
    if not _admin(callback.from_user.id):
        return await callback.answer("Admin only", show_alert=True)
    try:
        pid = _expand(callback.data.split(":",1)[1])
        p = (await session.execute(select(Product).where(Product.id==pid))).scalar_one_or_none()
        if not p: return await callback.answer("Not found", show_alert=True)

        meta = p.meta or {}
        emoji = _safe(meta.get("emoji", "📦"), 10)
        btn_en = _safe(meta.get("btn_en", ""), 50)
        usd = next((x.price for x in p.prices if x.currency=="USD"), None) if p.prices else None
        price_txt = f"  ${usd:.2f}" if usd else ""
        ps = _short(p.id)

        note_preview = _safe(meta.get("delivery_note_en", "Not set"), 30)
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="\u270f\ufe0f Edit Message", callback_data=f"cme_msg:{ps}"))
        kb.row(InlineKeyboardButton(text="\U0001f518 Edit Button + Emoji", callback_data=f"cme_btn:{ps}"))
        kb.row(InlineKeyboardButton(text="\U0001f4dd Edit Delivery Note", callback_data=f"cme_note:{ps}"))
        kb.row(InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="cme_products"))

        safe_name = _safe(p.name, 60)
        msg_text = (
            f"{emoji} <b>{safe_name}</b>{price_txt}\n\n"
            f"Button: <code>{btn_en or 'auto'}</code>\n"
            f"Note: <code>{note_preview}</code>\n\n"
            "Choose what to edit:"
        )
        try:
            await callback.message.edit_text(msg_text, reply_markup=kb.as_markup())
        except Exception as edit_err:
            logger.warning(f"[CMS] edit_text failed: {edit_err}, sending new message")
            await callback.message.answer(msg_text, reply_markup=kb.as_markup())
        await callback.answer()
    except Exception as e:
        logger.error(f"[CMS] cb_product CRASHED: {e}", exc_info=True)
        try:
            await callback.answer(f"Error: {str(e)[:100]}", show_alert=True)
        except:
            pass


# ── Edit product message ──────────────────────────────
@router.callback_query(F.data.startswith("cme_msg:"))
async def cb_msg(callback: CallbackQuery, session: AsyncSession, state: FSMContext, **kwargs):
    if not _admin(callback.from_user.id):
        return await callback.answer("Admin only", show_alert=True)
    try:
        pid = _expand(callback.data.split(":",1)[1])
        p = (await session.execute(select(Product).where(Product.id==pid))).scalar_one_or_none()
        if not p: return await callback.answer("Not found", show_alert=True)

        # Always use product_detail — this is what catalog.py renders
        tkey = "product_detail"
        tpl = (await session.execute(
            select(MessageTemplate).where(
                MessageTemplate.key == "product_detail",
                MessageTemplate.is_active == True,
                MessageTemplate.is_deleted == False,
            )
        )).scalar_one_or_none()

        if not tpl: return await callback.answer("product_detail not in DB", show_alert=True)

        ps = _short(p.id)
        await state.set_state(Edit.text_en)
        await state.update_data(tkey=tkey, mode="raw", back=f"cme_p:{ps}")

        ar = (tpl.content_i18n or {}).get("ar") if isinstance(tpl.content_i18n, dict) else None
        emoji = (p.meta or {}).get("emoji", "\U0001f4e6")

        # Use short alias for callback_data (max 64 bytes)
        # Store full tkey in state, use "pd" as short alias for product_detail
        cb_key = tkey[:48] if len(tkey) <= 48 else "product_detail"

        kb = InlineKeyboardBuilder()
        kb.row(
            InlineKeyboardButton(text="\U0001f4cb Copy EN", callback_data=f"cme_cp:{cb_key}:en"),
            InlineKeyboardButton(text="\U0001f4cb Copy AR", callback_data=f"cme_cp:{cb_key}:ar"),
        )
        kb.row(InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data=f"cme_p:{ps}"))

        msg_text = (
            f"{emoji} <b>{p.name}</b>\n<code>{tkey}</code>\n\n"
            f"\U0001f1ec\U0001f1e7 <b>EN:</b>\n<pre>{_safe(tpl.content)}</pre>\n\n"
            f"\U0001f1f8\U0001f1e6 <b>AR:</b>\n<pre>{_safe(ar) if ar else 'Not set'}</pre>"
        )

        try:
            await callback.message.edit_text(msg_text, reply_markup=kb.as_markup())
        except Exception as edit_err:
            logger.warning(f"[CMS] edit_text failed: {edit_err}, sending new message")
            await callback.message.answer(msg_text, reply_markup=kb.as_markup())

        await callback.message.answer(
            "✏️ Send new <b>English</b> text\n"
            "💡 Premium emojis & bold/italic formatting are captured automatically\n"
            "Or <code>skip</code> to keep current:",
            reply_markup=BACK_KB,
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"[CMS] cb_msg CRASHED: {e}", exc_info=True)
        try:
            await callback.answer(f"Error: {str(e)[:100]}", show_alert=True)
        except:
            pass


# ── Edit product button + emoji ───────────────────────
@router.callback_query(F.data.startswith("cme_btn:"))
async def cb_btn(callback: CallbackQuery, session: AsyncSession, state: FSMContext, **kwargs):
    if not _admin(callback.from_user.id):
        return await callback.answer("Admin only", show_alert=True)
    pid = _expand(callback.data.split(":",1)[1])
    p = (await session.execute(select(Product).where(Product.id==pid))).scalar_one_or_none()
    if not p: return await callback.answer("Not found", show_alert=True)

    meta = p.meta or {}
    ps = _short(p.id)
    await state.set_state(Edit.btn_emoji)
    await state.update_data(pid=str(p.id), ps=ps)

    await callback.message.edit_text(
        f"\U0001f518 <b>Edit Button: {p.name}</b>\n\n"
        f"Current emoji: <code>{meta.get('emoji','')}</code>\n"
        f"Current EN button: <code>{meta.get('btn_en','auto')}</code>\n\n"
        "<b>Step 1/3</b> — Send the emoji for this product\n"
        "(paste any emoji including premium Telegram emoji)\n"
        "Or <code>skip</code> to keep current:",
    )
    await callback.message.answer("Send emoji \u2193", reply_markup=BACK_KB)
    await callback.answer()


@router.message(Edit.btn_emoji)
async def recv_btn_emoji(message: Message, state: FSMContext, **kwargs):
    if not _admin(message.from_user.id): await state.clear(); return
    if message.text == BACK_TEXT:
        await state.clear()
        return await message.answer("Cancelled.", reply_markup=ReplyKeyboardRemove())

    # ── Capture emoji — support premium custom emoji, stickers, regular emoji ──
    emoji = None
    custom_emoji_id = None

    if message.sticker:
        # Sticker: check if it has a custom_emoji_id (premium sticker packs)
        if message.sticker.custom_emoji_id:
            custom_emoji_id = message.sticker.custom_emoji_id
        emoji = message.sticker.emoji or "🎭"

    elif message.text and message.text.strip().lower() == "skip":
        # Keep existing — don't update
        await state.update_data(new_emoji=None, new_custom_emoji_id=None)
        await state.set_state(Edit.btn_en)
        await message.answer(
            "<b>Step 2/3</b> — Send the <b>English</b> button text\n"
            "Example: <code>ChatGPT Plus | $2.00</code>\n\n"
            "⚠️ <b>Send text only</b> — no emojis or stickers here!\n"
            "Or <code>skip</code> to keep current:",
            reply_markup=BACK_KB,
        )
        return

    elif message.text:
        emoji = message.text.strip()
        # Check for premium custom emoji in entities
        if message.entities:
            for ent in message.entities:
                if ent.type == "custom_emoji":
                    custom_emoji_id = ent.custom_emoji_id
                    break

    else:
        await message.answer(
            "⚠️ Send a regular emoji, premium emoji, or sticker.\n"
            "Or send <code>skip</code> to keep current.",
            reply_markup=BACK_KB,
        )
        return

    await state.update_data(new_emoji=emoji, new_custom_emoji_id=custom_emoji_id)
    await state.set_state(Edit.btn_en)
    await message.answer(
        "<b>Step 2/3</b> — Send the <b>English</b> button text\n"
        "Example: <code>ChatGPT Plus | $2.00</code>\n\n"
        "⚠️ <b>Send text only</b> — do not send emojis or stickers here!\n"
        "Or <code>skip</code> to keep current:",
        reply_markup=BACK_KB,
    )


@router.message(Edit.btn_en)
async def recv_btn_en(message: Message, state: FSMContext, **kwargs):
    if not _admin(message.from_user.id): await state.clear(); return
    if message.text == BACK_TEXT:
        await state.clear()
        return await message.answer("Cancelled.", reply_markup=ReplyKeyboardRemove())

    # ── Reject non-text (stickers, photos, etc.) ──
    if not message.text:
        await message.answer(
            "⚠️ Please send <b>text</b>, not a sticker or media.\n"
            "Example: <code>ChatGPT Plus | $2.00</code>\n"
            "Or <code>skip</code> to keep current:",
            reply_markup=BACK_KB,
        )
        return

    # ── Reject if contains premium/custom emojis ──
    has_custom_emoji = any(
        e.type == "custom_emoji" for e in (message.entities or [])
    )
    if has_custom_emoji:
        await message.answer(
            "⚠️ <b>Button text cannot contain premium emojis</b> — this is a Telegram limitation.\n\n"
            "Premium emojis are already saved as the product icon and will show in the product list.\n"
            "For the button, send <b>plain text only</b>.\n"
            "Example: <code>ChatGPT Plus | $2.00</code>\n"
            "Or <code>skip</code> to use the default name:",
            reply_markup=BACK_KB,
        )
        return

    raw = message.text.strip()
    if raw.lower() == "skip":
        btn_en = None
    else:
        btn_en = raw

    await state.update_data(new_btn_en=btn_en)
    await state.set_state(Edit.btn_ar)
    await message.answer(
        "<b>Step 3/3</b> — Send the <b>Arabic</b> button text\n"
        "⚠️ Plain text only — no premium emojis\n"
        "Or <code>skip</code> to keep current:",
        reply_markup=BACK_KB,
    )


@router.message(Edit.btn_ar)
async def recv_btn_ar(message: Message, session: AsyncSession, state: FSMContext, **kwargs):
    if not _admin(message.from_user.id): await state.clear(); return
    if message.text == BACK_TEXT:
        await state.clear()
        return await message.answer("Cancelled.", reply_markup=ReplyKeyboardRemove())

    # ── Reject non-text ──
    if not message.text:
        await message.answer(
            "⚠️ Please send <b>text</b>, not a sticker.\n"
            "Or <code>skip</code> to keep current:",
            reply_markup=BACK_KB,
        )
        return

    # ── Reject premium emojis ──
    if any(e.type == "custom_emoji" for e in (message.entities or [])):
        await message.answer(
            "⚠️ <b>Button text cannot contain premium emojis.</b>\n"
            "Send plain text or <code>skip</code>:",
            reply_markup=BACK_KB,
        )
        return

    data = await state.get_data()
    pid = data["pid"]; ps = data["ps"]
    new_emoji = data.get("new_emoji")
    new_custom_emoji_id = data.get("new_custom_emoji_id")
    new_btn_en = data.get("new_btn_en")
    new_btn_ar = None if message.text.strip().lower() == "skip" else message.text.strip()

    p = (await session.execute(select(Product).where(Product.id==pid))).scalar_one_or_none()
    if not p:
        await message.answer("❌ Product not found.", reply_markup=ReplyKeyboardRemove())
        return await state.clear()

    meta = dict(p.meta) if p.meta else {}
    if new_emoji is not None:
        meta["emoji"] = new_emoji
        # Save custom emoji ID for <tg-emoji> rendering in messages
        if new_custom_emoji_id:
            meta["custom_emoji_id"] = new_custom_emoji_id
        elif "custom_emoji_id" in meta:
            del meta["custom_emoji_id"]  # clear if switching to regular emoji
    if new_btn_en is not None:    meta["btn_en"] = new_btn_en
    if new_btn_ar is not None:    meta["btn_ar"] = new_btn_ar
    p.meta = meta; flag_modified(p, "meta")

    try:
        await session.flush(); await session.commit()
        kb = InlineKeyboardBuilder()
        kb.row(
            InlineKeyboardButton(text="✏️ Edit Again", callback_data=f"cme_btn:{ps}"),
            InlineKeyboardButton(text="⬅️ Back", callback_data=f"cme_p:{ps}"),
        )
        await message.answer(
            f"✅ <b>Saved!</b>\n"
            f"Emoji: {meta.get('emoji','—')}\n"
            f"EN: <code>{meta.get('btn_en','auto')}</code>\n"
            f"AR: <code>{meta.get('btn_ar','auto')}</code>",
            reply_markup=kb.as_markup(),
        )
    except Exception as e:
        await session.rollback()
        await message.answer(f"\u274c Error: {e}", parse_mode=None)

    await state.clear()
    await message.answer("\u200b", reply_markup=ReplyKeyboardRemove())


# ── Edit Delivery Note ────────────────────────────────
@router.callback_query(F.data.startswith("cme_note:"))
async def cb_note(callback: CallbackQuery, session: AsyncSession, state: FSMContext, **kwargs):
    if not _admin(callback.from_user.id):
        return await callback.answer("Admin only", show_alert=True)
    pid = _expand(callback.data.split(":",1)[1])
    p = (await session.execute(select(Product).where(Product.id==pid))).scalar_one_or_none()
    if not p: return await callback.answer("Not found", show_alert=True)

    meta = p.meta or {}
    ps = _short(p.id)
    note_en = meta.get("delivery_note_en", "Not set")
    note_ar = meta.get("delivery_note_ar", "Not set")

    await state.set_state(Edit.note_en)
    await state.update_data(pid=str(p.id), ps=ps)

    await callback.message.edit_text(
        f"📝 <b>Edit Delivery Note: {p.name}</b>\n\n"
        f"This note appears in the delivery message after purchase.\n\n"
        f"🇬🇧 <b>Current EN Note:</b>\n<pre>{_safe(note_en)}</pre>\n\n"
        f"🇸🇦 <b>Current AR Note:</b>\n<pre>{_safe(note_ar)}</pre>",
    )
    await callback.message.answer(
        "<b>Step 1/2</b> — Send the <b>English</b> delivery note\n"
        "💡 This will appear as ⚠️ Note: ... in delivery messages\n"
        "Supports <b>bold</b>, <i>italic</i>, premium emojis\n\n"
        "Example:\n<code>HMA VPN key for PC/Android | 28-30 days.\n- Use 5 devices</code>\n\n"
        "Or <code>skip</code> to keep current:",
        reply_markup=BACK_KB,
    )
    await callback.answer()


@router.message(Edit.note_en)
async def recv_note_en(message: Message, state: FSMContext, **kwargs):
    if not _admin(message.from_user.id): await state.clear(); return
    if message.text == BACK_TEXT:
        await state.clear()
        return await message.answer("Cancelled.", reply_markup=ReplyKeyboardRemove())

    if message.text and message.text.strip().lower() == "skip":
        note_en = None
    else:
        note_en = _extract_text(message)

    await state.update_data(new_note_en=note_en)
    await state.set_state(Edit.note_ar)
    await message.answer(
        "<b>Step 2/2</b> — Send the <b>Arabic</b> delivery note\n"
        "Or <code>skip</code> to keep current:",
        reply_markup=BACK_KB,
    )


@router.message(Edit.note_ar)
async def recv_note_ar(message: Message, session: AsyncSession, state: FSMContext, **kwargs):
    if not _admin(message.from_user.id): await state.clear(); return
    if message.text == BACK_TEXT:
        await state.clear()
        return await message.answer("Cancelled.", reply_markup=ReplyKeyboardRemove())

    data = await state.get_data()
    pid = data["pid"]; ps = data["ps"]
    new_note_en = data.get("new_note_en")

    if message.text and message.text.strip().lower() == "skip":
        new_note_ar = None
    else:
        new_note_ar = _extract_text(message)

    p = (await session.execute(select(Product).where(Product.id==pid))).scalar_one_or_none()
    if not p:
        await message.answer("❌ Product not found.", reply_markup=ReplyKeyboardRemove())
        return await state.clear()

    meta = dict(p.meta) if p.meta else {}
    if new_note_en is not None:    meta["delivery_note_en"] = new_note_en
    if new_note_ar is not None:    meta["delivery_note_ar"] = new_note_ar
    p.meta = meta; flag_modified(p, "meta")

    try:
        await session.flush(); await session.commit()
        kb = InlineKeyboardBuilder()
        kb.row(
            InlineKeyboardButton(text="📝 Edit Again", callback_data=f"cme_note:{ps}"),
            InlineKeyboardButton(text="⬅️ Back", callback_data=f"cme_p:{ps}"),
        )
        en_preview = _safe(meta.get("delivery_note_en", "Not set"), 50)
        ar_preview = _safe(meta.get("delivery_note_ar", "Not set"), 50)
        await message.answer(
            f"✅ <b>Delivery Note Saved!</b>\n\n"
            f"🇬🇧 EN: <code>{en_preview}</code>\n"
            f"🇸🇦 AR: <code>{ar_preview}</code>",
            reply_markup=kb.as_markup(),
        )
    except Exception as e:
        await session.rollback()
        await message.answer(f"❌ Error: {e}", parse_mode=None)

    await state.clear()
    await message.answer("\u200b", reply_markup=ReplyKeyboardRemove())


@router.message(Edit.text_en)
async def recv_en(message: Message, session: AsyncSession, state: FSMContext, **kwargs):
    if not _admin(message.from_user.id): await state.clear(); return
    if message.text == BACK_TEXT:
        await state.clear()
        return await message.answer("Cancelled.", reply_markup=ReplyKeyboardRemove())

    data = await state.get_data()
    logger.info(f"[CMS] recv_en: tkey={data.get('tkey')}, has_text={bool(message.text)}, text_len={len(message.text or '')}")
    en = None
    if message.text and message.text.strip().lower() != "skip":
        en = _extract_text(message)   # captures bold + premium emoji + typed HTML
        logger.info(f"[CMS] recv_en: extracted en_len={len(en) if en else 0}, has_tg_emoji={'<tg-emoji' in (en or '')}")
    else:
        logger.info(f"[CMS] recv_en: SKIPPED (text={message.text!r})")
    await state.update_data(new_en=en)
    await state.set_state(Edit.text_ar)

    tpl = (await session.execute(
        select(MessageTemplate).where(MessageTemplate.key==data["tkey"])
    )).scalar_one_or_none()
    ar_cur = (tpl.content_i18n or {}).get("ar","") if tpl and isinstance(tpl.content_i18n, dict) else ""

    await message.answer(
        "🇸🇦 Now send <b>Arabic</b> text\n"
        "💡 Premium emojis work automatically — just paste or type\n"
        f"<b>Current:</b> <pre>{_safe(ar_cur)}</pre>\n\n"
        "Or <code>skip</code> to keep:",
        reply_markup=BACK_KB,
    )


# ── Receive AR text + save ────────────────────────────
@router.message(Edit.text_ar)
async def recv_ar(message: Message, session: AsyncSession, state: FSMContext, **kwargs):
    if not _admin(message.from_user.id): await state.clear(); return
    if message.text == BACK_TEXT:
        await state.clear()
        return await message.answer("Cancelled.", reply_markup=ReplyKeyboardRemove())

    data = await state.get_data()
    tkey = data["tkey"]
    new_en = data.get("new_en")
    logger.info(f"[CMS] recv_ar: tkey={tkey}, new_en_len={len(new_en) if new_en else 0}")
    ar = None
    if message.text and message.text.strip().lower() != "skip":
        ar = _extract_text(message)   # captures bold + premium emoji + typed HTML
        logger.info(f"[CMS] recv_ar: extracted ar_len={len(ar) if ar else 0}")
    else:
        logger.info(f"[CMS] recv_ar: SKIPPED")

    ok = await _save_tpl(session, tkey, en=new_en, ar=ar)
    logger.info(f"[CMS] recv_ar: _save_tpl returned ok={ok}")
    back = data.get("back","cme_main")
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="\u270f\ufe0f Edit Again", callback_data=f"cme_msg:{back.split(':')[-1]}" if "cme_p:" in back else "cme_pages"),
        InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data=back),
    )
    if ok:
        await message.answer(
            f"\u2705 <b>Saved!</b>  <code>{tkey}</code>\n\n"
            f"\U0001f50d Test: /msgpreview {tkey}",
            reply_markup=kb.as_markup(),
        )
    else:
        await message.answer(f"\u274c Could not save '{tkey}'.", reply_markup=ReplyKeyboardRemove())

    await state.clear()
    await message.answer("\u200b", reply_markup=ReplyKeyboardRemove())


# ── Pages list ────────────────────────────────────────
@router.callback_query(F.data == "cme_pages")
async def cb_pages(callback: CallbackQuery, **kwargs):
    if not _admin(callback.from_user.id):
        return await callback.answer("Admin only", show_alert=True)
    kb = InlineKeyboardBuilder()
    for key, label in PAGE_TEMPLATES.items():
        kb.row(InlineKeyboardButton(text=label, callback_data=f"cme_tpl:{key}"))
    kb.row(InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="cme_main"))
    await callback.message.edit_text(
        "\U0001f4c4 <b>Pages & Notifications</b>\n\nSelect a template:",
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


# ── Template edit ─────────────────────────────────────
@router.callback_query(F.data.startswith("cme_tpl:"))
async def cb_tpl(callback: CallbackQuery, session: AsyncSession, state: FSMContext, **kwargs):
    if not _admin(callback.from_user.id):
        return await callback.answer("Admin only", show_alert=True)
    tkey = callback.data.split(":",1)[1]
    tpl = (await session.execute(
        select(MessageTemplate).where(MessageTemplate.key==tkey)
    )).scalar_one_or_none()
    if not tpl: return await callback.answer(f"'{tkey}' not in DB", show_alert=True)

    await state.set_state(Edit.text_en)
    await state.update_data(tkey=tkey, mode="raw", back="cme_pages")

    ar = (tpl.content_i18n or {}).get("ar") if isinstance(tpl.content_i18n, dict) else None
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="\U0001f4cb Copy EN", callback_data=f"cme_cp:{tkey}:en"),
        InlineKeyboardButton(text="\U0001f4cb Copy AR", callback_data=f"cme_cp:{tkey}:ar"),
    )
    kb.row(InlineKeyboardButton(text="\U0001f4ce Telegram Format EN", callback_data=f"cme_tg:{tkey}:en"))
    kb.row(InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="cme_pages"))

    await callback.message.edit_text(
        f"\u270f\ufe0f <b>{PAGE_TEMPLATES.get(tkey, tkey)}</b>\n"
        f"<code>{tkey}</code>\n\n"
        f"\U0001f1ec\U0001f1e7 <b>EN:</b>\n<pre>{_safe(tpl.content)}</pre>\n\n"
        f"\U0001f1f8\U0001f1e6 <b>AR:</b>\n<pre>{_safe(ar) if ar else 'Not set'}</pre>",
        reply_markup=kb.as_markup(),
    )
    await callback.message.answer(
        "✏️ Send new <b>English</b> text\n"
        "💡 Premium emojis & bold/italic/code are captured automatically\n"
        "Or <code>skip</code>:",
        reply_markup=BACK_KB,
    )
    await callback.answer()


# ── Telegram format mode ──────────────────────────────
@router.callback_query(F.data.startswith("cme_tg:"))
async def cb_tg_mode(callback: CallbackQuery, state: FSMContext, **kwargs):
    parts = callback.data.split(":")
    tkey, lang = parts[1], parts[2]
    st = Edit.text_en if lang == "en" else Edit.text_ar
    await state.set_state(st)
    back = "cme_pages" if tkey in PAGE_TEMPLATES else "cme_products"
    await state.update_data(tkey=tkey, mode="tg", back=back, new_en=None)
    await callback.message.answer(
        "\U0001f4ce <b>Telegram Format</b>\nUse Ctrl+B for bold, paste premium emoji.\n"
        "Do NOT type &lt;b&gt; manually.\n\nSend text:",
        reply_markup=BACK_KB,
    )
    await callback.answer()


# ── Copy full content ─────────────────────────────────
@router.callback_query(F.data.startswith("cme_cp:"))
async def cb_copy(callback: CallbackQuery, session: AsyncSession, **kwargs):
    if not _admin(callback.from_user.id):
        return await callback.answer("Admin only", show_alert=True)
    parts = callback.data.split(":")
    tkey, lang = parts[1], parts[2]
    tpl = (await session.execute(
        select(MessageTemplate).where(MessageTemplate.key==tkey)
    )).scalar_one_or_none()
    if not tpl: return await callback.answer("Not found", show_alert=True)

    if lang == "ar":
        content = (tpl.content_i18n or {}).get("ar") if isinstance(tpl.content_i18n, dict) else None
        if not content: return await callback.answer("No Arabic content yet", show_alert=True)
        flag = "\U0001f1f8\U0001f1e6 AR"
    else:
        content = tpl.content; flag = "\U0001f1ec\U0001f1e7 EN"

    for i, chunk in enumerate([content[j:j+3500] for j in range(0, len(content), 3500)]):
        prefix = f"\U0001f4cb <b>{flag}</b>  <code>{tkey}</code>\n\n" if i==0 else ""
        await callback.message.answer(
            prefix + f"<pre>{chunk.replace('<','&lt;').replace('>','&gt;')}</pre>"
        )
    await callback.answer("Full content sent \u2193")


# ── Navigation ────────────────────────────────────────
@router.callback_query(F.data == "cme_main")
async def cb_main(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.clear(); await _main_menu(callback); await callback.answer()

@router.callback_query(F.data == "cme_close")
async def cb_close(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.clear()
    await callback.message.edit_text("\u2705 Editor closed.")
    await callback.answer()


# ── /msgpreview ───────────────────────────────────────
@router.message(Command("msgpreview"))
async def cmd_preview(message: Message, session: AsyncSession, **kwargs):
    if not _admin(message.from_user.id): return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /msgpreview key", parse_mode=None); return
    key = args[1].strip()
    test = {
        "store_name": settings.STORE_NAME, "user_name": message.from_user.first_name,
        "bot_username": (await message.bot.get_me()).username,
        "support_user": await __import__('bot_services.store_settings', fromlist=['get_setting']).get_setting(session, "support_user", settings.SUPPORT_USERNAME or "@admin"),
        "channel_url": settings.CHANNEL_URL or "N/A",
        "product_name": "Test Product", "emoji": "\U0001f4e6",
        "description": "Test description", "price_usd": "2.50",
        "stock": "10", "order_number": "ORDERTEST1", "qty": "2",
        "total_usd": "5.00", "amount": "5.00", "timeout": "30",
        "wallet_address": "195940195",
        "delivery_data": "<code>test@email.com:pass123</code>",
    }
    text = await cms.render(session, key, "en", **test)
    try:
        await message.answer(f"\U0001f4cb <b>[{key}]:</b>\n\n{text}")
    except Exception as e:
        safe = text.replace("<","&lt;").replace(">","&gt;")
        await message.answer(f"\u26a0\ufe0f {e}\n\n<pre>{safe[:800]}</pre>")


# ── /debugtpl — diagnose template issues ──────────────
@router.message(Command("debugtpl"))
async def cmd_debug_tpl(message: Message, session: AsyncSession, **kwargs):
    if not _admin(message.from_user.id): return
    key = "product_detail"
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        key = args[1].strip()

    # Find ALL templates with this key
    all_tpls = (await session.execute(
        select(MessageTemplate).where(MessageTemplate.key == key)
    )).scalars().all()

    if not all_tpls:
        await message.answer(f"❌ No templates with key <code>{key}</code>", parse_mode="HTML")
        return

    lines = [f"🔍 <b>Debug: {key}</b>\n"]
    for t in all_tpls:
        status = "✅" if (t.is_active and not t.is_deleted) else "❌"
        lines.append(
            f"{status} id=<code>{str(t.id)[:8]}</code> "
            f"active={t.is_active} deleted={t.is_deleted}\n"
            f"   content_len={len(t.content or '')} "
            f"has_tg_emoji={'<tg-emoji' in (t.content or '')}\n"
            f"   first_50: <code>{_safe(t.content, 50)}</code>\n"
        )

    # Also show all product emojis
    products = (await session.execute(
        select(Product).where(Product.is_deleted == False).limit(10)
    )).scalars().all()
    lines.append("\n📦 <b>Product Emoji Status:</b>\n")
    for p in products:
        meta = p.meta or {}
        lines.append(
            f"• {p.name[:25]}: emoji=<code>{meta.get('emoji','N/A')}</code> "
            f"custom_id=<code>{meta.get('custom_emoji_id','N/A')}</code>\n"
        )

    await message.answer("".join(lines), parse_mode="HTML")
