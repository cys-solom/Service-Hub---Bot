"""One-time script to create the Adobe Creative Cloud product in the database."""
import asyncio, sys, os

# Add backend to path
backend_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, backend_dir)

from core.database import get_session
from models.catalog import Product, ProductPrice, Category
from sqlalchemy import select

ADOBE_META = {
    "emoji":          "🎨",
    "delivery_type":  "api",
    "api_provider":   "adobe",
    "api_config": {
        "api_provider":   "adobe",
        "org_id":         "5658812D69E9267B0A495E74@AdobeOrg",
        "client_id":      "de6266fdac3b405696967d06a1f61c7d",
        "client_secret":  "p8e-87loOAYUxmEKr4OI6DGRkbikhFa_gDaB",
    },
    # Preset quantity buttons (months)
    "qty_presets": [1, 4, 12],
    "qty_labels": {
        "1":  "🗓 1 Month",
        "4":  "📅 4 Months",
        "12": "🏆 1 Year",
    },
    # Email prompt
    "input_label_en": "📧 Enter your Adobe account email address to activate your subscription:",
    "input_label_ar": "📧 أدخل بريدك الإلكتروني المرتبط بحساب Adobe لتفعيل الاشتراك:",
}

NAMES_I18N = {
    "en": "Adobe Creative Cloud",
    "ar": "أدوبي كريتيف كلاود",
}

DESCS_I18N = {
    "en": (
        "🎨 <b>Adobe Creative Cloud</b>\n\n"
        "Access 20+ premium apps — Photoshop, Illustrator, Premiere Pro & more!\n\n"
        "💡 <b>How it works:</b>\n"
        "• Enter your Adobe account email\n"
        "• Subscription is activated instantly\n"
        "• Every 1 unit = 1 month of access\n\n"
        "📦 <b>Available plans:</b>\n"
        "• 1 Month  — $1.50\n"
        "• 4 Months — $6.00\n"
        "• 12 Months (1 Year) — $18.00\n"
        "• Or choose any custom number of months"
    ),
    "ar": (
        "🎨 <b>أدوبي كريتيف كلاود</b>\n\n"
        "وصول لأكثر من 20 تطبيق احترافي — فوتوشوب، إليستريتور، بريمير برو والمزيد!\n\n"
        "💡 <b>كيف يعمل:</b>\n"
        "• أدخل البريد الإلكتروني لحساب Adobe\n"
        "• يتم التفعيل فوراً\n"
        "• كل وحدة = شهر واحد من الوصول\n\n"
        "📦 <b>الباقات المتاحة:</b>\n"
        "• شهر واحد — 1.50 دولار\n"
        "• 4 أشهر — 6.00 دولار\n"
        "• 12 شهراً (سنة كاملة) — 18.00 دولار\n"
        "• أو اختر عدد أشهر مخصص"
    ),
}


async def main():
    async with get_session() as db:
        # Check if already exists
        existing = (await db.execute(
            select(Product).where(Product.name == "Adobe Creative Cloud")
        )).scalar_one_or_none()

        if existing:
            print(f"✅ Product already exists: {existing.id}")
            # Update meta
            existing.meta           = ADOBE_META
            existing.names_i18n     = NAMES_I18N
            existing.descriptions_i18n = DESCS_I18N
            existing.description    = DESCS_I18N["en"]
            await db.commit()
            print("✅ Updated meta, names and descriptions.")

            # Update price
            price = (await db.execute(
                select(ProductPrice).where(ProductPrice.product_id == existing.id)
            )).scalar_one_or_none()
            if price:
                price.price = 1.50
                await db.commit()
                print("✅ Price updated to $1.50/month")
            return

        # Find or create "Subscriptions" category
        cat = (await db.execute(
            select(Category).where(Category.is_deleted == False).order_by(Category.sort_order)
        )).scalars().first()

        if not cat:
            cat = Category(name="Subscriptions", slug="subscriptions", sort_order=0)
            db.add(cat)
            await db.flush()
            print(f"Created new category: {cat.name}")
        else:
            print(f"Using category: {cat.name} ({cat.id})")

        # Create product
        product = Product(
            name               = "Adobe Creative Cloud",
            slug               = "adobe-cc",
            category_id        = str(cat.id),
            description        = DESCS_I18N["en"],
            names_i18n         = NAMES_I18N,
            descriptions_i18n  = DESCS_I18N,
            stock_type         = "api",
            delivery_mode      = "auto",
            is_visible         = True,
            force_out_of_stock = False,
            min_qty            = 1,
            max_qty            = 60,
            meta               = ADOBE_META,
        )
        db.add(product)
        await db.flush()

        # Create price $1.50/month
        db.add(ProductPrice(
            product_id = product.id,
            currency   = "USD",
            price      = 1.50,
            label      = "per month",
        ))
        await db.commit()

        print(f"✅ Created Adobe CC product! ID: {product.id}")
        print(f"   Price: $1.50/month")
        print(f"   Presets: 1 month / 4 months / 12 months (+ custom)")


asyncio.run(main())
