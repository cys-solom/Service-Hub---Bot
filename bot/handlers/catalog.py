"""Catalog handler — MMO Store style with CMS templates"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
from models.catalog import Category, Product, ProductPrice
from models.stock import StockItem

from config import settings
from keyboards import product_list_kb, product_detail_kb, back_kb
from bot_services import cms
from bot_services.store_settings import get_store_vars

router = Router()


def _render_emoji(meta: dict) -> str:
    """Render emoji for message text — supports premium custom emojis.
    Buttons can't use <tg-emoji>, but message text can."""
    fallback = meta.get("emoji", "📦")
    cid = meta.get("custom_emoji_id")
    if cid:
        return f'<tg-emoji emoji-id="{cid}">{fallback}</tg-emoji>'
    return fallback


async def _get_products_data(session):
    """Get all visible products with prices and stock counts"""
    products = (await session.execute(
        select(Product).where(Product.is_visible == True, Product.is_deleted == False)
        .order_by(Product.sort_order, Product.name)
    )).scalars().all()

    prices_map = {}
    stock_map = {}

    for p in products:
        price = (await session.execute(
            select(ProductPrice).where(
                ProductPrice.product_id == p.id,
                ProductPrice.is_deleted == False,
            ).limit(1)
        )).scalar_one_or_none()
        prices_map[str(p.id)] = price.price if price else 0

        meta = p.meta or {}
        is_api = meta.get("delivery_type") == "api"
        is_unlimited = (not is_api and meta.get("unlimited") is True)
        if is_api and not p.force_out_of_stock:
            # API products: use real stock from meta if available
            stock_map[str(p.id)] = meta.get("stock", 999999)
        elif is_unlimited and not p.force_out_of_stock:
            stock_map[str(p.id)] = 999999
        else:
            stock = (await session.execute(
                select(func.count(StockItem.id))
                .where(StockItem.product_id == p.id, StockItem.is_sold == False, StockItem.is_deleted == False)
            )).scalar() or 0
            stock_map[str(p.id)] = 0 if p.force_out_of_stock else stock

    return products, prices_map, stock_map


async def show_products_list(event, session: AsyncSession, lang: str = "en"):
    """Show numbered product list — uses CMS templates"""
    products, prices_map, stock_map = await _get_products_data(session)

    # Filter out API products with 0 stock (they shouldn't appear in SHOP)
    products = [p for p in products if stock_map.get(str(p.id), 0) > 0]

    sv = await get_store_vars(session, settings)
    support_user = sv["support_user"]
    store_name = sv["store_name"]

    msg = event if isinstance(event, Message) else event.message

    # ── No products fallback ──
    if not products:
        if lang == "ar":
            text = (
                "📭 <b>لا توجد منتجات</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "لا توجد منتجات متاحة حالياً.\n"
                "يرجى المحاولة لاحقاً أو التواصل مع الدعم.\n\n"
                f"💬 الدعم: {support_user}"
            )
        else:
            text = (
                "📭 <b>No Products Available</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "There are no products available right now.\n"
                "Please check again later or contact support.\n\n"
                f"💬 Support: {support_user}"
            )
        kb = back_kb("menu:back", lang)
        if isinstance(event, CallbackQuery):
            await msg.edit_text(text, reply_markup=kb)
            await event.answer()
        else:
            await msg.answer(text, reply_markup=kb)
        return

    # Clean welcome message instead of verbose product list
    product_count = len(products)
    if lang == "ar":
        text = (
            f"🛍 <b>{store_name}</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"📦 <b>{product_count}</b> منتج متاح\n\n"
            "اختر المنتج اللي عايزه من الأزرار 👇\n\n"
            f"💬 الدعم: {support_user}"
        )
    else:
        text = (
            f"🛍 <b>{store_name}</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"📦 <b>{product_count}</b> products available\n\n"
            "Choose a product below 👇\n\n"
            f"💬 Support: {support_user}"
        )

    kb = product_list_kb(products, prices_map, stock_map, "USD", lang)

    if isinstance(event, CallbackQuery):
        await msg.edit_text(text, reply_markup=kb)
        await event.answer()
    else:
        await msg.answer(text, reply_markup=kb)


@router.message(Command("products"))
async def cmd_products(message: Message, session: AsyncSession, lang: str = "en"):
    await show_products_list(message, session, lang)


@router.callback_query(F.data == "menu:products")
async def cb_products(callback: CallbackQuery, session: AsyncSession, lang: str = "en"):
    await show_products_list(callback, session, lang)


@router.callback_query(F.data == "menu:refresh_stock")
async def cb_refresh_stock(callback: CallbackQuery, session: AsyncSession, lang: str = "en"):
    """Fetch live stock from Reseller API and update all API products"""
    import httpx, os, logging
    from sqlalchemy.orm.attributes import flag_modified
    logger = logging.getLogger(__name__)

    await callback.answer(
        "🔄 Refreshing stock from API..." if lang == "en" else "🔄 جاري تحديث المخزون...",
    )

    try:
        base_url = os.environ.get("RESELLER_API_BASE_URL", "").strip()
        api_key = os.environ.get("RESELLER_API_KEY", "").strip()

        if not base_url or not api_key:
            await callback.answer("API not configured", show_alert=True)
            return

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{base_url}?action=products", headers=headers)
            data = resp.json()

        api_products = data.get("products", [])
        if not api_products:
            await callback.answer("No products from API", show_alert=True)
            return

        # Build lookup: api_id -> {stock, available, price}
        api_lookup = {}
        for ap in api_products:
            api_lookup[ap["id"]] = {
                "stock": ap.get("stock", 0),
                "available": ap.get("available", False),
                "price": ap.get("price", 0),
            }

        # Update all API products in DB
        db_products = (await session.execute(
            select(Product).where(
                Product.provider_product_code.isnot(None),
                Product.is_deleted == False,
            )
        )).scalars().all()

        updated = 0
        for p in db_products:
            api_data = api_lookup.get(p.provider_product_code)
            if not api_data:
                continue

            meta = p.meta or {}
            new_stock = api_data["stock"] if api_data["available"] else 0

            if meta.get("stock") != new_stock or meta.get("cost_price") != api_data["price"]:
                meta["stock"] = new_stock
                meta["cost_price"] = api_data["price"]
                p.meta = meta
                flag_modified(p, "meta")
                updated += 1

        await session.commit()
        logger.info(f"[Catalog] Stock refreshed: {updated} products updated from API")

    except Exception as e:
        import traceback
        logger.error(f"[Catalog] Stock refresh failed: {e}\n{traceback.format_exc()}")

    # Re-display product list with updated stock
    await show_products_list(callback, session, lang)


@router.callback_query(F.data.startswith("prod:"))
async def show_product_detail(callback: CallbackQuery, session: AsyncSession, lang: str = "en"):
    import logging, traceback
    logger = logging.getLogger(__name__)
    logger.info(f"[Catalog] prod: callback received — data={callback.data}")
    
    product_id = callback.data.split(":")[1]

    try:
        product = (await session.execute(
            select(Product).where(Product.id == product_id)
        )).scalar_one_or_none()
        if not product:
            await callback.answer("Product not found", show_alert=True)
            return

        is_api = (product.meta or {}).get("delivery_type") == "api"

        # API products: use real stock from meta if available
        if is_api and not product.force_out_of_stock:
            stock_count = (product.meta or {}).get("stock", 999999)
        else:
            stock_count = (await session.execute(
                select(func.count(StockItem.id))
                .where(StockItem.product_id == product.id, StockItem.is_sold == False, StockItem.is_deleted == False)
            )).scalar() or 0
            if product.force_out_of_stock:
                stock_count = 0

        # ── Block if out of stock ──
        if stock_count == 0:
            alert_msg = "❌ This product is currently out of stock.\nPlease check back later!" if lang == "en" \
                else "❌ هذا المنتج غير متوفر حالياً.\nيرجى المحاولة لاحقاً!"
            await callback.answer(alert_msg, show_alert=True)
            return

        sold_count = (await session.execute(
            select(func.count(StockItem.id))
            .where(StockItem.product_id == product.id, StockItem.is_sold == True)
        )).scalar() or 0

        price = (await session.execute(
            select(ProductPrice).where(ProductPrice.product_id == product.id, ProductPrice.is_deleted == False).limit(1)
        )).scalar_one_or_none()
        price_usd = price.price if price else 0

        name = product.names_i18n.get(lang, product.name) if product.names_i18n else product.name
        desc = product.descriptions_i18n.get(lang, product.description) if product.descriptions_i18n else (product.description or "")
        emoji = _render_emoji(product.meta or {})
        bonus = (product.meta or {}).get("bonus", "")
        bonus_text = f"🎁 Bonus: {bonus}" if bonus else ""

        # Stock display
        if stock_count == 999999:
            stock_display = "∞"
            stock_emoji = "✅"
        elif stock_count > 5:
            stock_display = str(stock_count)
            stock_emoji = "✅"
        elif stock_count > 0:
            stock_display = str(stock_count)
            stock_emoji = "⚠️"
        else:
            stock_display = "0"
            stock_emoji = "❌"

        text = await cms.render(session, "product_detail", lang,
                                emoji=emoji, product_name=name, description=desc,
                                price_usd=f"{price_usd:.2f}", stock=stock_display,
                                stock_emoji=stock_emoji, sold=sold_count,
                                bonus_text=bonus_text)

        # For display in keyboard: pass actual count (999999 means unlimited → show buttons)
        await callback.message.edit_text(
            text, reply_markup=product_detail_kb(product_id, stock_count, lang, product_meta=product.meta),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"[Catalog] prod: handler CRASHED: {e}\n{traceback.format_exc()}")
        try:
            await callback.answer(f"Error: {str(e)[:100]}", show_alert=True)
        except Exception:
            pass


