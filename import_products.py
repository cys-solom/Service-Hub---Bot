"""
Import products from VEX Reseller API into local database.

Safety:
- Read-only against the Reseller API (only fetches products list)
- Does NOT call place_order
- Does NOT change payment/delivery logic
- API key loaded from env only, never stored in DB
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
PROVIDER_NAME = "VEX Reseller API"
PROVIDER_CODE = "vex_reseller"


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


async def fetch_api_products() -> list:
    """Fetch products from Reseller API (read-only)"""
    import httpx

    base_url = os.environ.get("RESELLER_API_BASE_URL", "").strip()
    api_key = os.environ.get("RESELLER_API_KEY", "").strip()

    if not base_url or not api_key:
        print("ERROR: RESELLER_API_BASE_URL and RESELLER_API_KEY must be set in .env")
        return []

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{base_url}?action=products", headers=headers)
        data = resp.json()

    if not data.get("success", True) and "error" in data:
        print(f"API error: {data['error']}")
        return []

    return data.get("products", [])


def is_importable(p: dict) -> bool:
    """Filter: available=True, is_active not False, stock > 0"""
    if not p.get("available"):
        return False
    if p.get("is_active") is False:  # None is OK (API returns None for active products)
        return False
    if (p.get("stock") or 0) <= 0:
        return False
    return True


async def main():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import select
    from models import Base
    from models.catalog import Category, Product, ProductPrice
    from models.provider import ExternalProvider, ProviderProduct

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

    # ── Step 1: Fetch API products ──
    print("\n[2/5] Fetching products from Reseller API...")
    all_products = await fetch_api_products()
    if not all_products:
        print("  No products returned from API.")
        await engine.dispose()
        return

    importable = [p for p in all_products if is_importable(p)]
    skipped_api = len(all_products) - len(importable)

    print(f"  Total from API: {len(all_products)}")
    print(f"  Importable (available, active, stock>0): {len(importable)}")
    print(f"  Skipped (unavailable/no stock): {skipped_api}")

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
                api_url=os.environ.get("RESELLER_API_BASE_URL", ""),
                is_enabled=True,
                description="VEX Reseller API provider for digital products",
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
            api_id = p["id"]
            api_name = p.get("name", "Unknown").strip()
            api_price = float(p.get("price", 0))
            api_stock = int(p.get("stock", 0))
            api_manual = bool(p.get("manual_delivery", False))
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
                    # Force SQLAlchemy to detect the change
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(existing, "meta")
                    updated += 1
                    status = "UPDATED"
                else:
                    skipped_exists += 1
                    status = "SKIPPED (unchanged)"

                # Update ProviderProduct availability
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
                    # Get existing price
                    ep = (await session.execute(
                        select(ProductPrice).where(
                            ProductPrice.product_id == existing.id,
                            ProductPrice.is_deleted == False,
                        ).limit(1)
                    )).scalar_one_or_none()
                    samples.append((api_name, api_price, ep.price if ep else local_price, api_stock, status))
                continue

            # ── Create new product ──
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
                        "api_provider": "vex_reseller",
                    },
                    "source": "reseller_api",
                    "cost_price": api_price,
                    "stock": api_stock,
                    "manual_delivery": api_manual,
                    "emoji": "\U0001f916",
                },
            )
            session.add(product)
            await session.flush()  # Get product.id

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
    print(f"\n[5/5] Import complete!")
    print(f"  {'='*50}")
    print(f"  Products fetched from API:  {len(all_products)}")
    print(f"  Importable:                 {len(importable)}")
    print(f"  Created (new):              {created}")
    print(f"  Updated (meta only):        {updated}")
    print(f"  Skipped (already exists):   {skipped_exists}")
    print(f"  Skipped (API filter):       {skipped_api}")
    print(f"  Category:                   {CATEGORY_NAME}")
    print(f"  Provider:                   {PROVIDER_NAME}")
    print(f"  Markup:                     {MARKUP_PERCENT*100:.0f}% (min profit ${MINIMUM_PROFIT:.2f})")
    print(f"  {'='*50}")

    if samples:
        print(f"\n  Sample imported products:")
        print(f"  {'Name':<35} {'Cost':>8} {'Local':>8} {'Stock':>6} {'Status'}")
        print(f"  {'-'*80}")
        for name, cost, local, stock, status in samples:
            print(f"  {name[:34]:<35} ${cost:>7.2f} ${local:>7.2f} {stock:>6} {status}")

    print(f"\n  ** No reseller place_order was called **")
    print(f"  ** No payment/delivery logic was changed **")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
