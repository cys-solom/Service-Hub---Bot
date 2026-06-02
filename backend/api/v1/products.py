"""Products CRUD API"""
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.config import settings
from core.security import get_current_admin
from core.telegram import send_telegram
from models.catalog import Product, ProductPrice, Category
from models.stock import StockItem
from models.cms import MessageTemplate

router = APIRouter(prefix="/products", tags=["products"])
logger = logging.getLogger(__name__)


class ProductIn(BaseModel):
    name: str
    slug: str = ""
    description: Optional[str] = None
    image_url: Optional[str] = None
    category_id: Optional[str] = None
    stock_type: str = "code"
    delivery_mode: str = "auto"
    is_visible: bool = True
    force_out_of_stock: bool = False
    sort_order: int = 0
    min_qty: int = 1
    max_qty: int = 100
    bonus_qty: int = 0
    bonus_threshold: int = 0
    reply_template: Optional[str] = None
    names_i18n: Optional[dict] = None
    descriptions_i18n: Optional[dict] = None
    meta: Optional[dict] = None          # API config, emoji, delivery_type, etc.
    prices: list[dict] = []  # [{"currency": "USD", "price": 10.0}]


@router.get("")
async def list_products(
    category_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Product).where(Product.is_deleted == False)
    if category_id:
        query = query.where(Product.category_id == uuid.UUID(category_id))
    query = query.order_by(Product.sort_order, Product.name)
    result = await db.execute(query)
    products = result.scalars().all()

    items = []
    for p in products:
        stock_avail = (await db.execute(
            select(func.count(StockItem.id))
            .where(StockItem.product_id == p.id, StockItem.is_sold == False, StockItem.is_deleted == False)
        )).scalar() or 0
        stock_total = (await db.execute(
            select(func.count(StockItem.id))
            .where(StockItem.product_id == p.id, StockItem.is_deleted == False)
        )).scalar() or 0

        # Get prices
        prices_result = await db.execute(
            select(ProductPrice).where(ProductPrice.product_id == p.id, ProductPrice.is_deleted == False)
        )
        prices = [{"id": str(pp.id), "currency": pp.currency, "price": pp.price,
                    "old_price": pp.old_price, "min_qty": pp.min_qty, "max_qty": pp.max_qty}
                   for pp in prices_result.scalars().all()]

        is_api = (p.meta or {}).get("delivery_type") == "api"
        items.append({
            "id": str(p.id), "name": p.name, "slug": p.slug,
            "description": p.description, "image_url": p.image_url,
            "category_id": str(p.category_id),
            "stock_type": p.stock_type, "delivery_mode": p.delivery_mode,
            "is_visible": p.is_visible, "force_out_of_stock": p.force_out_of_stock,
            "sort_order": p.sort_order,
            "min_qty": p.min_qty, "max_qty": p.max_qty,
            "bonus_qty": p.bonus_qty, "bonus_threshold": p.bonus_threshold,
            "reply_template": p.reply_template,
            "names_i18n": p.names_i18n, "descriptions_i18n": p.descriptions_i18n,
            "meta": p.meta,
            "stock_available": 999999 if (is_api and not p.force_out_of_stock) else (0 if p.force_out_of_stock else stock_avail),
            "stock_total": stock_total,
            "prices": prices,
        })
    return {"products": items}


class ReorderItem(BaseModel):
    id: str
    sort_order: int

class ReorderRequest(BaseModel):
    items: list[ReorderItem]

@router.put("/reorder")
async def reorder_products(
    data: ReorderRequest, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    for item in data.items:
        product = (await db.execute(
            select(Product).where(Product.id == uuid.UUID(item.id))
        )).scalar_one_or_none()
        if product:
            product.sort_order = item.sort_order
    await db.commit()
    return {"success": True}


@router.post("")
async def create_product(
    data: ProductIn, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    import re as _re
    # Generate clean slug — remove special chars, limit length
    raw_slug = data.slug or data.name.lower().replace(" ", "-")
    raw_slug = _re.sub(r'[^a-z0-9\-]', '', raw_slug)  # keep only a-z, 0-9, -
    raw_slug = _re.sub(r'-+', '-', raw_slug).strip('-')[:80]  # collapse dashes, max 80 chars
    if not raw_slug:
        raw_slug = f"product-{uuid.uuid4().hex[:8]}"

    # Ensure unique slug
    slug = raw_slug
    suffix = 1
    while True:
        existing = (await db.execute(
            select(Product.id).where(Product.slug == slug)
        )).scalar_one_or_none()
        if not existing:
            break
        slug = f"{raw_slug}-{suffix}"
        suffix += 1

    # Auto-resolve category — find or create default
    cat_id = None
    if data.category_id:
        cat_id = uuid.UUID(data.category_id)
    else:
        # Find or create a default "General" category
        default_cat = (await db.execute(
            select(Category).where(Category.is_deleted == False).order_by(Category.sort_order).limit(1)
        )).scalar_one_or_none()
        if not default_cat:
            default_cat = Category(name="General", slug="general", sort_order=0)
            db.add(default_cat)
            await db.flush()
        cat_id = default_cat.id

    product = Product(
        name=data.name, slug=slug, description=data.description,
        image_url=data.image_url, category_id=cat_id,
        stock_type=data.stock_type, delivery_mode=data.delivery_mode,
        is_visible=data.is_visible, force_out_of_stock=data.force_out_of_stock,
        sort_order=data.sort_order,
        min_qty=data.min_qty, max_qty=data.max_qty,
        bonus_qty=data.bonus_qty, bonus_threshold=data.bonus_threshold,
        reply_template=data.reply_template,
        names_i18n=data.names_i18n, descriptions_i18n=data.descriptions_i18n,
        meta=data.meta,
    )
    db.add(product)
    await db.flush()

    price_lines = []
    for p in data.prices:
        db.add(ProductPrice(
            product_id=product.id,
            currency=p.get("currency", "USD"),
            price=p["price"],
            old_price=p.get("old_price"),
            min_qty=p.get("min_qty", 1),
            max_qty=p.get("max_qty", 999),
        ))
        price_lines.append(f"${p['price']:.2f} {p.get('currency', 'USD')}")

    # Note: All products use the shared "product_detail" template with placeholders
    # ({emoji}, {product_name}, {price_usd}, etc.). Per-product customization
    # comes from product fields, not separate templates.
    template_key = f"product_{slug}"  # kept for admin notification only

    await db.commit()
    await db.refresh(product)

    # Build public notification via CMS or fallback
    price_display = " / ".join(price_lines) if price_lines else "Coming soon"
    from core.cms import render as cms_render
    public_msg = await cms_render(db, "notify_product_added", "en",
                                  product_name=product.name,
                                  price=price_display,
                                  description=product.description or "Premium digital product")
    if not public_msg:
        public_msg = (
            f"🆕 <b>New Product Available!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"📦  <b>{product.name}</b>\n\n"
            f"💰  Price: <b>{price_display}</b>\n"
            f"📝  {product.description or 'Premium digital product'}\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🛒 <b>Order now from the bot!</b>"
        )

    # Broadcast to all bot users
    from models.user import User
    all_users = (await db.execute(
        select(User).where(User.is_banned == False, User.is_deleted == False)
    )).scalars().all()
    sent = 0
    for u in all_users:
        try:
            await send_telegram(u.telegram_id, public_msg)
            sent += 1
        except Exception:
            pass
    logger.info(f"[Product] Broadcast sent to {sent}/{len(all_users)} users")

    # Send detailed admin notification
    admin_gid = settings.ADMIN_GROUP_ID
    if admin_gid:
        admin_msg = (
            f"🆕 <b>Product Created</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"🏷  <b>{product.name}</b>\n"
            f"💰  {price_display}\n"
            f"📦  {product.stock_type} · {product.delivery_mode}\n"
            f"👁  {'Visible' if product.is_visible else 'Hidden'}\n"
            f"✏️  <code>{template_key}</code>\n"
            f"📣  Broadcast: {sent}/{len(all_users)} users\n\n"
            f"#product #new"
        )
        await send_telegram(int(admin_gid), admin_msg)

    logger.info(f"[Product] ✅ Created '{product.name}' (template: {template_key})")
    return {"success": True, "id": str(product.id)}


@router.put("/{product_id}")
async def update_product(
    product_id: str, data: ProductIn,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    product = (await db.execute(
        select(Product).where(Product.id == uuid.UUID(product_id))
    )).scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")

    # Preserve bot-managed meta fields when admin updates
    BOT_META_KEYS = {"custom_emoji_id", "emoji", "btn_en", "btn_ar",
                     "delivery_note_en", "delivery_note_ar"}

    for field in ["name", "description", "image_url", "stock_type", "delivery_mode",
                  "is_visible", "force_out_of_stock", "sort_order", "min_qty", "max_qty",
                  "bonus_qty", "bonus_threshold", "reply_template", "names_i18n",
                  "descriptions_i18n"]:
        val = getattr(data, field, None)
        if val is not None:
            setattr(product, field, val)

    # Merge meta — keep bot-managed keys, update admin keys
    if data.meta is not None:
        existing_meta = dict(product.meta) if product.meta else {}
        new_meta = dict(data.meta)
        # Preserve bot-managed keys that admin didn't send
        for k in BOT_META_KEYS:
            if k in existing_meta and k not in new_meta:
                new_meta[k] = existing_meta[k]
        product.meta = new_meta
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(product, "meta")

    if data.slug:
        product.slug = data.slug
    if data.category_id:
        product.category_id = uuid.UUID(data.category_id)

    # Update prices
    if data.prices:
        for p_data in data.prices:
            currency = p_data.get("currency", "USD")
            price_val = p_data.get("price", 0)
            existing = (await db.execute(
                select(ProductPrice).where(
                    ProductPrice.product_id == product.id,
                    ProductPrice.currency == currency,
                    ProductPrice.is_deleted == False,
                )
            )).scalar_one_or_none()
            if existing:
                existing.price = price_val
            else:
                db.add(ProductPrice(product_id=product.id, currency=currency, price=price_val))

    await db.commit()
    return {"success": True}


@router.delete("/{product_id}")
async def delete_product(
    product_id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    product = (await db.execute(
        select(Product).where(Product.id == uuid.UUID(product_id))
    )).scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")
    product.is_deleted = True
    await db.commit()
    return {"success": True}
