"""Dynamic keyboard builder — MMO Store style"""
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


# ─── Language Selection ──────────────────────────────
def language_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ English 🇬🇧", callback_data="lang:en", style="primary"),
        InlineKeyboardButton(text="🇸🇦 العربية", callback_data="lang:ar", style="primary"),
    )
    return builder.as_markup()


# ─── Dynamic Button Cache ────────────────────────────
import httpx
import logging
_logger = logging.getLogger(__name__)

_btn_cache = {"reply": None, "inline": None, "_ts": 0}

async def _fetch_buttons():
    """Fetch buttons from backend API with 60s cache"""
    import time
    now = time.time()
    if _btn_cache["reply"] is not None and now - _btn_cache["_ts"] < 60:
        return _btn_cache
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8000/api/v1/reply-buttons/public", timeout=3)
            data = resp.json()
            _btn_cache["reply"] = data.get("reply", [])
            _btn_cache["inline"] = data.get("inline", [])
            _btn_cache["_ts"] = now
    except Exception as e:
        _logger.debug(f"Backend API not available, using fallback buttons: {e}")
        if _btn_cache["reply"] is None:
            # Hardcoded fallback
            _btn_cache["reply"] = [
                {"key": "shop", "text_en": "Shop", "text_ar": "المتجر", "emoji": "🛍", "action": "shop", "row_order": 0, "col_order": 0},
                {"key": "menu", "text_en": "Menu", "text_ar": "القائمة", "emoji": "📋", "action": "menu", "row_order": 0, "col_order": 1},
                {"key": "wallet", "text_en": "Wallet", "text_ar": "المحفظة", "emoji": "💰", "action": "wallet", "row_order": 1, "col_order": 0},
                {"key": "topup", "text_en": "Top up", "text_ar": "شحن", "emoji": "🏦", "action": "topup", "row_order": 1, "col_order": 1},
                {"key": "orders", "text_en": "Order history", "text_ar": "سجل الطلبات", "emoji": "📦", "action": "orders", "row_order": 2, "col_order": 0},
            ]
            _btn_cache["inline"] = [
                {"key": "i_shop", "text_en": "SHOP", "text_ar": "المتجر", "emoji": "🛍", "action": "shop", "row_order": 0, "col_order": 0},
                {"key": "i_wallet", "text_en": "WALLET", "text_ar": "المحفظة", "emoji": "💰", "action": "wallet", "row_order": 1, "col_order": 0},
                {"key": "i_topup", "text_en": "TOPUP", "text_ar": "شحن", "emoji": "🏦", "action": "topup", "row_order": 1, "col_order": 1},
                {"key": "i_orders", "text_en": "ORDER HISTORY", "text_ar": "سجل الطلبات", "emoji": "📦", "action": "orders", "row_order": 2, "col_order": 0},
                {"key": "i_referral", "text_en": "REFERRAL", "text_ar": "الإحالة", "emoji": "👥", "action": "referral", "row_order": 3, "col_order": 0},
                {"key": "i_apikey", "text_en": "API KEY", "text_ar": "API Key", "emoji": "🔑", "action": "apikey", "row_order": 3, "col_order": 1},
                {"key": "i_language", "text_en": "LANGUAGE", "text_ar": "اللغة", "emoji": "🌐", "action": "language", "row_order": 4, "col_order": 0},
                {"key": "i_support", "text_en": "SUPPORT", "text_ar": "الدعم", "emoji": "💬", "action": "support", "row_order": 4, "col_order": 1},
            ]
    return _btn_cache

def invalidate_btn_cache():
    """Force refresh next time"""
    _btn_cache["_ts"] = 0


ACTION_MAP = {
    "shop": "menu:products",
    "wallet": "menu:wallet",
    "topup": "menu:topup",
    "orders": "menu:orders",
    "referral": "menu:referral",
    "apikey": "menu:apikey",
    "language": "menu:language",
    "support": "menu:support",
}


# ─── Main Menu (Inline) — DB-driven ─────────────────
# Style map for main menu buttons by action
_MENU_STYLE = {
    "shop": "success",
    "wallet": "primary",
    "topup": "success",
    "orders": "primary",
    "referral": "primary",
    "apikey": "primary",
    "language": "primary",
    "support": "primary",
}


async def main_menu_inline_kb(lang="en", group_url=None, support_username=None):
    cache = await _fetch_buttons()
    builder = InlineKeyboardBuilder()

    if group_url:
        builder.row(InlineKeyboardButton(text="🏠 JOIN GROUP", url=group_url, style="primary"))

    inline_btns = cache.get("inline", [])
    # Group by row_order
    rows = {}
    for b in inline_btns:
        r = b["row_order"]
        if r not in rows:
            rows[r] = []
        rows[r].append(b)

    for row_idx in sorted(rows.keys()):
        row_btns = sorted(rows[row_idx], key=lambda x: x["col_order"])
        row_items = []
        for b in row_btns:
            text = f"{b['emoji']} {b['text_ar'] if lang == 'ar' else b['text_en']}"
            callback_data = ACTION_MAP.get(b["action"], f"menu:{b['action']}")
            style = _MENU_STYLE.get(b["action"], "primary")
            row_items.append(InlineKeyboardButton(text=text, callback_data=callback_data, style=style))
        if row_items:
            builder.row(*row_items)

    return builder.as_markup()


# ─── Main Menu (Reply Keyboard) — DB-driven ─────────
async def main_menu_reply_kb(lang="en"):
    cache = await _fetch_buttons()
    builder = ReplyKeyboardBuilder()

    reply_btns = cache.get("reply", [])
    rows = {}
    for b in reply_btns:
        r = b["row_order"]
        if r not in rows:
            rows[r] = []
        rows[r].append(b)

    for row_idx in sorted(rows.keys()):
        row_btns = sorted(rows[row_idx], key=lambda x: x["col_order"])
        row_items = []
        for b in row_btns:
            text = f"{b['emoji']} {b['text_ar'] if lang == 'ar' else b['text_en']}"
            row_items.append(KeyboardButton(text=text))
        if row_items:
            builder.row(*row_items)

    return builder.as_markup(resize_keyboard=True, is_persistent=True)


def get_all_reply_texts(cache):
    """Get all possible reply button texts for matching"""
    texts = {}
    for b in cache.get("reply", []):
        texts[f"{b['emoji']} {b['text_en']}"] = b["action"]
        texts[f"{b['emoji']} {b['text_ar']}"] = b["action"]
        texts[f"{b['emoji']} {b['text_en'].upper()}"] = b["action"]
    return texts




# ─── Product List Buttons ────────────────────────────
def product_list_kb(products, prices_map, stock_map, currency="USD", lang="en"):
    """Build product buttons — supports custom text per product via product.meta btn_en/btn_ar"""
    builder = InlineKeyboardBuilder()
    for p in products:
        meta = p.meta or {}
        emoji = meta.get("emoji", "📦")
        custom_emoji_id = meta.get("custom_emoji_id")  # premium emoji ID
        price_usd = prices_map.get(str(p.id), 0)
        stock = stock_map.get(str(p.id), 0)

        # Use custom button label or product name
        custom_btn = meta.get(f"btn_{lang}") or meta.get("btn_en")
        name = custom_btn or (p.names_i18n.get(lang, p.name) if p.names_i18n else p.name)

        # Truncate name if too long
        if len(name) > 35:
            name = name[:32] + "..."

        # Stock suffix + button style
        if stock == 999999:
            suffix = f" | ${price_usd:.2f} (∞)"
            btn_style = "success"
        elif stock > 0:
            suffix = f" | ${price_usd:.2f} ({stock} left)"
            btn_style = "success"
        else:
            suffix = f" | ${price_usd:.2f} (out of stock)"
            btn_style = "danger"

        # If custom emoji available → use icon_custom_emoji_id (no emoji in text)
        # Otherwise → prepend regular emoji to text
        if custom_emoji_id:
            display = f"{name}{suffix}"
            builder.row(InlineKeyboardButton(
                text=display,
                callback_data=f"prod:{p.id}",
                icon_custom_emoji_id=str(custom_emoji_id),
                style=btn_style,
            ))
        else:
            display = f"{emoji} {name}{suffix}"
            builder.row(InlineKeyboardButton(
                text=display,
                callback_data=f"prod:{p.id}",
                style=btn_style,
            ))

    builder.row(InlineKeyboardButton(
        text="🔄 Refresh Stock" if lang == "en" else "🔄 تحديث المخزون",
        callback_data="menu:refresh_stock",
        style="primary",
    ))
    builder.row(InlineKeyboardButton(
        text="💰 My wallet" if lang == "en" else "💰 محفظتي",
        callback_data="menu:wallet",
        style="primary",
    ))
    builder.row(InlineKeyboardButton(
        text="🔙 Back" if lang == "en" else "🔙 رجوع",
        callback_data="menu:back",
        style="danger",
    ))
    return builder.as_markup()


# ─── Product Detail + Quantity ───────────────────────
def product_detail_kb(product_id, stock_count, lang="en", product_meta=None):
    """Quantity buttons — supports qty_presets from product.meta (e.g. Adobe months)"""
    builder = InlineKeyboardBuilder()
    meta = product_meta or {}
    is_api = meta.get("delivery_type") == "api"
    presets = meta.get("qty_presets")  # e.g. [1, 4, 12]
    preset_labels = meta.get("qty_labels")  # e.g. {"1": "1 Month", "4": "4 Months", "12": "1 Year"}

    available = is_api or stock_count > 0

    if available and presets:
        # Show preset quantity buttons — simple numbers
        for q in presets:
            label = preset_labels.get(str(q)) if preset_labels else None
            if not label:
                label = str(q)
            builder.button(text=label, callback_data=f"qty:{product_id}:{q}", style="success")
        builder.adjust(len(presets))
        builder.row(InlineKeyboardButton(
            text="✏️ Custom quantity" if lang == "en" else "✏️ كمية مخصصة",
            callback_data=f"qty_custom:{product_id}",
            style="primary",
        ))

    elif available:
        # Normal stock-based quantity buttons
        max_q = min(stock_count, 99) if not is_api else 99
        quick = [q for q in [1, 2, 3] if q <= max_q]
        for q in quick:
            builder.button(text=str(q), callback_data=f"qty:{product_id}:{q}", style="success")
        builder.adjust(3)

        row2 = [q for q in [5, 10] if q <= max_q]
        for q in row2:
            builder.button(text=str(q), callback_data=f"qty:{product_id}:{q}", style="success")
        if row2:
            builder.adjust(3, 2)

        builder.row(InlineKeyboardButton(
            text="✏️ Custom quantity" if lang == "en" else "✏️ كمية مخصصة",
            callback_data=f"qty_custom:{product_id}",
            style="primary",
        ))

    builder.row(InlineKeyboardButton(
        text="⬅️ Back" if lang == "en" else "⬅️ رجوع",
        callback_data="menu:products",
        style="danger",
    ))
    return builder.as_markup()


# ─── Order Summary (Coupon or Pay) ───────────────────
def order_summary_kb(order_id, lang="en"):
    """Show 'Use Coupon' and 'Pay' after quantity selection"""
    oid = _short_id(order_id)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🎟 Use Coupon" if lang == "en" else "🎟 استخدام كوبون",
        callback_data=f"coupon:{oid}",
        style="primary",
    ))
    builder.row(InlineKeyboardButton(
        text="💳 Pay Now" if lang == "en" else "💳 ادفع الآن",
        callback_data=f"gopay:{oid}",
        style="success",
    ))
    builder.row(InlineKeyboardButton(
        text="❌ Cancel" if lang == "en" else "❌ إلغاء",
        callback_data=f"cancel_order:{oid}",
        style="danger",
    ))
    return builder.as_markup()


def _short_id(uid):
    """Strip dashes from UUID to fit Telegram 64-byte callback limit"""
    return str(uid).replace('-', '')


# ─── Payment Methods ─────────────────────────────────
def payment_methods_kb(methods, order_id, total_egp=0, total_usd=0, lang="en", product_id=None):
    builder = InlineKeyboardBuilder()
    for m in methods:
        code = m.code
        if code == "wallet":
            continue  # handled separately
        icon = _payment_icon(code)
        if "egp" in code.lower() or "vodafone" in code.lower() or "instapay" in code.lower():
            label = f"{icon} {m.name} ({total_egp:.0f} EGP)"
        else:
            label = f"{icon} {m.name} ~ ${total_usd:.2f}"
        builder.row(InlineKeyboardButton(
            text=label,
            callback_data=f"pay:{order_id}:{code}",
            style="primary",
        ))

    # Wallet always last
    has_wallet = any(m.code == "wallet" for m in methods)
    if has_wallet:
        builder.row(InlineKeyboardButton(
            text=f"💰 Wallet Balance ~ ${total_usd:.2f}",
            callback_data=f"pay:{order_id}:wallet",
            style="success",
        ))

    oid = _short_id(order_id)
    builder.row(InlineKeyboardButton(
        text="❌ Cancel order" if lang == "en" else "❌ إلغاء الطلب",
        callback_data=f"cancel_order:{oid}",
        style="danger",
    ))
    return builder.as_markup()


def _payment_icon(code):
    icons = {
        "usdt_trc20": "💎",
        "usdt_bep20": "💎",
        "btc": "₿",
        "vodafone": "📱",
        "instapay": "🏦",
        "binance": "💫",
        "wallet": "💰",
    }
    return icons.get(code, "💳")


# ─── Payment Instructions ────────────────────────────
def payment_cancel_kb(order_id, lang="en"):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="✅ I Paid" if lang == "en" else "✅ دفعت",
        callback_data=f"paid:{order_id}",
        style="success",
    ))
    builder.row(InlineKeyboardButton(
        text="❌ Cancel order" if lang == "en" else "❌ إلغاء الطلب",
        callback_data=f"cancel_order:{order_id}",
        style="danger",
    ))
    return builder.as_markup()


# ─── Wallet ──────────────────────────────────────────
def wallet_kb(lang="en"):
    builder = InlineKeyboardBuilder()
    if lang == "ar":
        builder.row(InlineKeyboardButton(text="💰 إيداع", callback_data="wallet:deposit", style="success"))
        builder.row(InlineKeyboardButton(text="📊 سجل المعاملات", callback_data="wallet:history", style="primary"))
    else:
        builder.row(InlineKeyboardButton(text="💰 Deposit", callback_data="wallet:deposit", style="success"))
        builder.row(InlineKeyboardButton(text="📊 Transaction History", callback_data="wallet:history", style="primary"))
    builder.row(InlineKeyboardButton(text="⬅️ Back", callback_data="menu:back", style="danger"))
    return builder.as_markup()


def deposit_amounts_kb(lang="en"):
    builder = InlineKeyboardBuilder()
    for amount in [5, 10, 25, 50, 100]:
        builder.button(text=f"${amount}", callback_data=f"deposit_amount:{amount}", style="success")
    builder.adjust(3)
    builder.row(InlineKeyboardButton(
        text="✏️ Custom Amount" if lang == "en" else "✏️ مبلغ مخصص",
        callback_data="deposit_amount:custom",
        style="primary",
    ))
    builder.row(InlineKeyboardButton(text="⬅️ Back", callback_data="menu:wallet", style="danger"))
    return builder.as_markup()


# ─── Confirm / Cancel ────────────────────────────────
def confirm_kb(action, param="", lang="en"):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Confirm", callback_data=f"confirm:{action}:{param}", style="success"),
        InlineKeyboardButton(text="❌ Cancel", callback_data=f"cancel:{action}:{param}", style="danger"),
    )
    return builder.as_markup()


# ─── Back Button ─────────────────────────────────────
def back_kb(callback_data="menu:back", lang="en"):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Back", callback_data=callback_data, style="danger"))
    return builder.as_markup()
