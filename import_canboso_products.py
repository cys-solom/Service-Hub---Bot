"""Import products from Canboso API into local database.

Safety:
- Read-only against the Canboso API (only fetches products list)
- Does NOT change payment/delivery logic
- API key loaded from env or default fallback, never stored in DB
- Idempotent: safe to run multiple times
- Does NOT delete any data
- Does NOT overwrite manually-changed local prices
"""
import asyncio
import math
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "bot"))

from dotenv import load_dotenv
load_dotenv()

# ── Config ──
MARKUP_PERCENT = 0.35       # 35%
MINIMUM_PROFIT = 1.00       # $1.00 USDT
CATEGORY_NAME = "AI & Digital Services"
CATEGORY_SLUG = "ai-digital-services"
PROVIDER_NAME = "Canboso API"
PROVIDER_CODE = "canboso"


def calculate_local_price(api_price: float) -> float:
    """local_price = max(api_price * 1.35, api_price + 1.00), rounded to 2 decimals"""
    return round(max(api_price * (1 + MARKUP_PERCENT), api_price + MINIMUM_PROFIT), 2)


def slugify(name: str) -> str:
    """Convert product name to URL-safe slug"""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")[:200]


def map_emoji(emoji_name: str) -> str:
    """Map Canboso emoji string to Unicode emoji"""
    mapping = {
        "google": "✨",
        "google_one": "✨",
        "youtube": "📺",
        "capcut": "🎬",
        "grok": "🤖",
        "cursor": "💻",
        "antigravity": "🌌",
        "higgfield": "📹",
    }
    return mapping.get(emoji_name.lower().strip(), "📦")


async def main():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import select
    from models.catalog import Category, Product, ProductPrice
    from models.provider import ExternalProvider, ProviderProduct
    from bot_services.canboso_api import get_products

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL not set in .env")
        return

    safe_url = db_url.split("@")[1] if "@" in db_url else "***"
    print(f"[1/5] Connecting to DB: ...@{safe_url}")

    engine_kwargs = {"pool_pre_ping": True}
    if "supabase" in db_url:
        engine_kwargs["pool_size"] = 5
        engine_kwargs["max_overflow"] = 2
        engine_kwargs["connect_args"] = {
            "prepared_statement_cache_size": 0,
            "statement_cache_size": 0,
        }

    engine = create_async_engine(db_url, **engine_kwargs)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    # ── Step 1: Fetch Canboso API products ──
    print("\n[2/5] Fetching products from Canboso API...")
    try:
        api_data = await get_products()
        all_products = api_data.get("products", [])
    except Exception as e:
        print(f"ERROR fetching products: {e}")
        await engine.dispose()
        return

    if not all_products:
        print("  No products returned from Canboso API.")
        await engine.dispose()
        return

    # Filter: stock > 0, not hidden
    importable = []
    for p in all_products:
        # Check stock in stats.available
        stats = p.get("stats") or {}
        stock = int(stats.get("available") or 0)
        hidden = bool(p.get("hiddenInBotMenu", False))
        usd_price = p.get("usdPricing") or p.get("walletPricing") or 0.0

        if stock > 0 and not hidden and usd_price > 0:
            importable.append(p)

    skipped_api = len(all_products) - len(importable)

    print(f"  Total from API: {len(all_products)}")
    print(f"  Importable (stock > 0, not hidden): {len(importable)}")
    print(f"  Skipped: {skipped_api}")

    if not importable:
        print("  Nothing to import.")
        await engine.dispose()
        return

    # ── Step 2: Ensure provider exists ──
    print("\n[3/5] Setting up provider and category...")
    async with SessionLocal() as session:
        # Provider
        provider = (await session.execute(
            select(ExternalProvider).where(ExternalProvider.code == PROVIDER_CODE)
        )).scalar_one_or_none()

        if not provider:
            provider = ExternalProvider(
                name=PROVIDER_NAME,
                code=PROVIDER_CODE,
                api_url="https://canboso.com",
                is_enabled=True,
                description="Canboso API digital products provider",
            )
            session.add(provider)
            await session.flush()
            print(f"  + Created provider: {PROVIDER_NAME} (id={provider.id})")
        else:
            print(f"  = Provider exists: {PROVIDER_NAME} (id={provider.id})")

        # Category
        category = (await session.execute(
            select(Category).where(Category.slug == CATEGORY_SLUG)
        )).scalar_one_or_none()

        if not category:
            category = Category(
                name=CATEGORY_NAME,
                slug=CATEGORY_SLUG,
                description="AI tools, developer tools, and digital services",
                is_visible=True,
                sort_order=1,
            )
            session.add(category)
            await session.flush()
            print(f"  + Created category: {CATEGORY_NAME} (id={category.id})")
        else:
            print(f"  = Category exists: {CATEGORY_NAME} (id={category.id})")

        await session.commit()
        provider_id = str(provider.id)
        category_id = str(category.id)

    # ── Step 3: Import products ──
    print(f"\n[4/5] Importing {len(importable)} products...")
    created = 0
    updated = 0
    skipped_exists = 0
    samples = []

    async with SessionLocal() as session:
        for p in importable:
            api_id = p["_id"]
            api_name = p.get("product_name", "Unknown").strip()
            api_price = float(p.get("usdPricing") or p.get("walletPricing") or 0.0)
            stats = p.get("stats") or {}
            api_stock = int(stats.get("available") or 0)
            api_emoji = map_emoji(p.get("emoji") or "none")
            
            local_price = calculate_local_price(api_price)
            slug = slugify(api_name)

            # Check if product already exists by provider_product_code
            existing = (await session.execute(
                select(Product).where(
                    Product.provider_product_code == api_id,
                    Product.is_deleted == False,
                )
            )).scalar_one_or_none()

            if existing:
                # Update stock/meta reference fields only, NOT local price
                meta = existing.meta or {}
                changed = False

                if meta.get("stock") != api_stock:
                    meta["stock"] = api_stock
                    changed = True
                if meta.get("cost_price") != api_price:
                    meta["cost_price"] = api_price
                    changed = True

                if changed:
                    existing.meta = meta
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(existing, "meta")
                    updated += 1
                    status = "UPDATED"
                else:
                    skipped_exists += 1
                    status = "SKIPPED (unchanged)"

                # Update ProviderProduct
                pp = (await session.execute(
                    select(ProviderProduct).where(
                        ProviderProduct.external_code == api_id,
                        ProviderProduct.provider_id == provider_id,
                    )
                )).scalar_one_or_none()
                if pp:
                    pp.cost_price = api_price
                    pp.is_available = True

                if len(samples) < 5:
                    ep = (await session.execute(
                        select(ProductPrice).where(
                            ProductPrice.product_id == existing.id,
                            ProductPrice.is_deleted == False,
                        ).limit(1)
                    )).scalar_one_or_none()
                    samples.append((api_name, api_price, ep.price if ep else local_price, api_stock, status))
                continue

            # Create new product
            product = Product(
                name=api_name,
                slug=slug,
                category_id=category_id,
                is_visible=True,
                delivery_mode="api",
                provider_id=provider_id,
                provider_product_code=api_id,
                min_qty=1,
                max_qty=100,
                sort_order=created,
                meta={
                    "delivery_type": "api",
                    "api_config": {
                        "api_provider": PROVIDER_CODE,
                    },
                    "source": "canboso_api",
                    "cost_price": api_price,
                    "stock": api_stock,
                    "emoji": api_emoji,
                },
            )
            session.add(product)
            await session.flush()

            # Create price
            price_record = ProductPrice(
                product_id=product.id,
                price=local_price,
                currency="USD",
            )
            session.add(price_record)

            # Create provider product mapping
            provider_product = ProviderProduct(
                provider_id=provider_id,
                external_code=api_id,
                name=api_name,
                cost_price=api_price,
                is_available=True,
                product_id=product.id,
            )
            session.add(provider_product)

            created += 1
            if len(samples) < 5:
                samples.append((api_name, api_price, local_price, api_stock, "CREATED"))

        await session.commit()

    # ── Step 4: Report ──
    print(f"\n[5/5] Canboso Import complete!")
    print(f"  {'='*50}")
    print(f"  Products fetched:           {len(all_products)}")
    print(f"  Importable (stock>0):       {len(importable)}")
    print(f"  Created (new):              {created}")
    print(f"  Updated:                    {updated}")
    print(f"  Skipped (exists):           {skipped_exists}")
    print(f"  {'='*50}")

    if samples:
        print(f"\n  Sample Canboso products:")
        print(f"  {'Name':<35} {'Cost':>8} {'Local':>8} {'Stock':>6} {'Status'}")
        print(f"  {'-'*80}")
        for name, cost, local, stock, status in samples:
            # Safely print on Windows terminal (replacing unicode characters if needed)
            safe_name = name.encode("ascii", "replace").decode()
            print(f"  {safe_name[:34]:<35} ${cost:>7.2f} ${local:>7.2f} {stock:>6} {status}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
