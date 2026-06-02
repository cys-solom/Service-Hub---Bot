"""Insert Adobe CC product via raw SQL."""
import asyncio, sys, os, json, uuid
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))

from core.database import get_session
from sqlalchemy import text

META = json.dumps({
    "emoji": "art",
    "delivery_type": "api",
    "api_provider": "adobe",
    "api_config": {
        "api_provider":  "adobe",
        "org_id":        "5658812D69E9267B0A495E74@AdobeOrg",
        "client_id":     "de6266fdac3b405696967d06a1f61c7d",
        "client_secret": "p8e-87loOAYUxmEKr4OI6DGRkbikhFa_gDaB"
    },
    "qty_presets": [1, 4, 12],
    "qty_labels": {"1": "1 Month", "4": "4 Months", "12": "1 Year"},
    "input_label_en": "Enter your Adobe account email to activate subscription:",
    "input_label_ar": "ادخل بريدك الالكتروني لحساب Adobe للتفعيل:"
})
NAMES = json.dumps({"en": "Adobe Creative Cloud", "ar": "ادوبي كريتيف كلاود"})
DESCS = json.dumps({
    "en": "Adobe CC subscription. Each unit = 1 month. Plans: 1m $1.50 | 4m $6.00 | 12m $18.00",
    "ar": "اشتراك Adobe CC. كل وحدة = شهر. الباقات: شهر 1.50 | 4 اشهر 6 | 12 شهر 18 دولار"
})


async def go():
    async with get_session() as db:
        cat_row = (await db.execute(text(
            "SELECT id FROM categories WHERE is_deleted=false LIMIT 1"
        ))).first()
        if not cat_row:
            print("ERROR: no category found")
            return
        cat_id = str(cat_row[0])

        ex = (await db.execute(text(
            "SELECT id FROM products WHERE name='Adobe Creative Cloud'"
        ))).first()

        if ex:
            pid = str(ex[0])
            await db.execute(text(
                "UPDATE products SET meta=:m, names_i18n=:n, descriptions_i18n=:d WHERE id=:id"
            ), {"m": META, "n": NAMES, "d": DESCS, "id": pid})
            await db.execute(text(
                "UPDATE product_prices SET price=1.50 WHERE product_id=:id"
            ), {"id": pid})
            await db.commit()
            print("UPDATED product", pid)
            return

        pid = str(uuid.uuid4())
        slug = "adobe-cc-" + pid[:6]

        await db.execute(text("""
            INSERT INTO products
              (id, name, slug, category_id, description,
               names_i18n, descriptions_i18n,
               stock_type, delivery_mode,
               is_visible, force_out_of_stock,
               sort_order, min_qty, max_qty,
               bonus_qty, bonus_threshold,
               meta, is_deleted, created_at, updated_at)
            VALUES
              (:id, :name, :slug, :cat, 'Adobe CC subscription',
               :n, :d,
               'api', 'auto',
               true, false,
               99, 1, 60,
               0, 0,
               :m, false, NOW(), NOW())
        """), {
            "id":   pid,
            "name": "Adobe Creative Cloud",
            "slug": slug,
            "cat":  cat_id,
            "n":    NAMES,
            "d":    DESCS,
            "m":    META,
        })

        price_id = str(uuid.uuid4())
        await db.execute(text("""
            INSERT INTO product_prices
              (id, product_id, currency, price, min_qty, max_qty,
               is_deleted, created_at, updated_at)
            VALUES
              (:id, :pid, 'USD', 1.50, 1, 9999,
               false, NOW(), NOW())
        """), {"id": price_id, "pid": pid})

        await db.commit()
        print("CREATED product ID:", pid)
        print("Price: $1.50 / month")


asyncio.run(go())
