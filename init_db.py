"""
Safe database initialization script.
- Creates ALL tables from SQLAlchemy models (does NOT drop existing tables)
- Seeds default data using the existing seed_defaults() function
- Safe to run multiple times (idempotent)
"""
import asyncio
import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "bot"))

from dotenv import load_dotenv
load_dotenv()

async def main():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from models import Base  # imports ALL model classes
    
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL not set in .env")
        return
    
    # Mask password in output
    safe_url = db_url.split("@")[1] if "@" in db_url else "***"
    print(f"[1/3] Connecting to: ...@{safe_url}")
    
    engine_kwargs = {
        "pool_pre_ping": True,
    }
    if "pooler.supabase" in db_url or "supabase" in db_url:
        engine_kwargs["pool_size"] = 5
        engine_kwargs["max_overflow"] = 2
        engine_kwargs["connect_args"] = {
            "prepared_statement_cache_size": 0,
            "statement_cache_size": 0,
        }
    
    engine = create_async_engine(db_url, **engine_kwargs)
    
    # Step 1: Test connection
    try:
        async with engine.connect() as conn:
            version = await conn.scalar(
                __import__("sqlalchemy").text("SELECT version()")
            )
            print(f"  Connected: {version[:50]}")
    except Exception as e:
        print(f"  Connection FAILED: {e}")
        return
    
    # Step 2: Create all tables (safe — only creates missing tables, never drops)
    print(f"\n[2/3] Creating tables ({len(Base.metadata.tables)} tables defined)...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Verify
    from sqlalchemy import text
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
        )
        tables = result.fetchall()
        print(f"  Created {len(tables)} tables:")
        for t in tables:
            print(f"    OK {t[0]}")
    
    # Step 3: Seed defaults
    print(f"\n[3/3] Seeding default data...")
    
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    async with SessionLocal() as session:
        await _manual_seed(session)
    
    await engine.dispose()
    print("\nDatabase initialization complete!")


async def _manual_seed(session):
    """Full seed — languages, settings, 18 templates, payment methods, delivery rule"""
    from sqlalchemy import select
    from models.system import AppSetting, Language
    from models.cms import MessageTemplate
    from models.payment import PaymentMethod
    from models.delivery import DeliveryRule

    inserted = 0

    # 1. Languages
    existing = (await session.execute(select(Language))).scalars().all()
    if not existing:
        session.add(Language(code="en", name="English", native_name="English", is_default=True, is_enabled=True, flag_emoji="\U0001f1ec\U0001f1e7"))
        session.add(Language(code="ar", name="Arabic", native_name="\u0627\u0644\u0639\u0631\u0628\u064a\u0629", is_rtl=True, is_default=False, is_enabled=True, flag_emoji="\U0001f1f8\U0001f1e6"))
        print("    + Languages: en, ar")

    # 2. Core settings
    settings_list = [
        ("support_user",    "@eng_solom",     "store", "Support username"),
        ("store_name",      "Service Hub",    "store", "Store name"),
        ("channel_url",     "https://t.me/",  "store", "Channel URL"),
        ("payment_timeout", "30",             "store", "Payment timeout minutes"),
        ("referral_enabled",            "true",  "referral", "Enable referral system"),
        ("referral_commission_percent", "5",     "referral", "Referral commission %"),
        ("referral_min_order_amount",   "0",     "referral", "Min order for commission"),
        ("referral_auto_credit",        "true",  "referral", "Auto-credit referrer"),
        ("referral_max_invites",        "0",     "referral", "Max invites (0=unlimited)"),
    ]
    for key, value, group, desc in settings_list:
        exists = (await session.execute(
            select(AppSetting).where(AppSetting.key == key)
        )).scalar_one_or_none()
        if not exists:
            session.add(AppSetting(key=key, value=value, type="string", group=group, description=desc))
            print(f"    + Setting: {key}={value}")

    # 3. All 18 message templates (exact content from seed.py)
    default_messages = [
        ("welcome", "text", "bot",
         "\U0001f44b Welcome to <b>{store_name}</b>\n\n"
         "Please choose the display language for the bot.\n"
         "You can change it any time with /languages\n\n"
         "\U0001f465 Refer friends and earn <b>5%</b> commission!\n"
         "\U0001f517 {ref_link}",
         {"ar": "\U0001f44b \u0645\u0631\u062d\u0628\u0627\u064b \u0628\u0643 \u0641\u064a <b>{store_name}</b>\n\n"
          "\u0627\u062e\u062a\u0631 \u0644\u063a\u0629 \u0627\u0644\u0639\u0631\u0636 \u0644\u0644\u0628\u0648\u062a.\n"
          "\u064a\u0645\u0643\u0646\u0643 \u062a\u063a\u064a\u064a\u0631\u0647\u0627 \u0641\u064a \u0623\u064a \u0648\u0642\u062a \u0645\u0646 /languages\n\n"
          "\U0001f465 \u0634\u0627\u0631\u0643 \u0627\u0644\u0631\u0627\u0628\u0637 \u0648\u0627\u0631\u0628\u062d <b>5%</b> \u0639\u0645\u0648\u0644\u0629!\n"
          "\U0001f517 {ref_link}"}),

        ("main_menu", "text", "bot",
         "\U0001f3ea <b>{store_name}</b>\n\n"
         "\U0001f916 Bot Auto 24/7: @{bot_username}\n"
         "\U0001f468\u200d\U0001f4bc Admin: {support_user}\n\n"
         "\U0001f517 Join Group: {channel_url}\n\n"
         "<b>Quick commands:</b>\n"
         "\U0001f6cd Product list: /products\n"
         "\U0001f4b0 Wallet: /wallet /deposit\n"
         "\U0001f4e6 Order history: /myorders\n"
         "\U0001f465 Refer friends: /ref\n"
         "\U0001f511 Stock API: /apikey\n"
         "\U0001f3ab Send Ticket: /support\n"
         "\U0001f4cb Main menu: /menu\n"
         "\U0001f310 Change language: /languages\n\n"
         "\U0001f4cc Use keyboard below for quick access:",
         {"ar": "\U0001f3ea <b>{store_name}</b>\n\n"
          "\U0001f916 \u0628\u0648\u062a 24/7: @{bot_username}\n"
          "\U0001f468\u200d\U0001f4bc \u0627\u0644\u0623\u062f\u0645\u0646: {support_user}\n\n"
          "\U0001f517 \u0627\u0646\u0636\u0645 \u0644\u0644\u062c\u0631\u0648\u0628: {channel_url}\n\n"
          "<b>\u0623\u0648\u0627\u0645\u0631 \u0633\u0631\u064a\u0639\u0629:</b>\n"
          "\U0001f6cd \u0627\u0644\u0645\u0646\u062a\u062c\u0627\u062a: /products\n"
          "\U0001f4b0 \u0627\u0644\u0645\u062d\u0641\u0638\u0629: /wallet /deposit\n"
          "\U0001f4e6 \u0627\u0644\u0637\u0644\u0628\u0627\u062a: /myorders\n"
          "\U0001f3ab \u0625\u0631\u0633\u0627\u0644 \u062a\u0630\u0643\u0631\u0629: /support\n"
          "\U0001f4cb \u0627\u0644\u0642\u0627\u0626\u0645\u0629: /menu\n"
          "\U0001f310 \u0627\u0644\u0644\u063a\u0629: /languages"}),

        ("product_list_header", "text", "bot",
         "\U0001f4cb <b>PRODUCT LIST - {store_name}</b>",
         {"ar": "\U0001f4cb <b>\u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0645\u0646\u062a\u062c\u0627\u062a - {store_name}</b>"}),

        ("product_list_item", "text", "bot",
         "<b>{index}.</b> {emoji} {product_name}\n"
         "   \u2514 USD: <b>${price_usd}</b> | \U0001f4e6 Avail: <b>{stock}</b>",
         {"ar": "<b>{index}.</b> {emoji} {product_name}\n"
          "   \u2514 \u0627\u0644\u0633\u0639\u0631: <b>${price_usd}</b> | \U0001f4e6 \u0627\u0644\u0645\u062a\u0627\u062d: <b>{stock}</b>"}),

        ("product_list_footer", "text", "bot",
         "\n\U0001f4ac Quick commands: /products /wallet /deposit /myorders /menu /languages\n"
         "\U0001f468\u200d\U0001f4bc Admin contact: {support_user}\n"
         "Choose a product below:",
         {"ar": "\n\U0001f4ac \u0623\u0648\u0627\u0645\u0631 \u0633\u0631\u064a\u0639\u0629: /products /wallet /deposit /myorders /menu /languages\n"
          "\U0001f468\u200d\U0001f4bc \u0627\u0644\u0623\u062f\u0645\u0646: {support_user}\n"
          "\u0627\u062e\u062a\u0631 \u0645\u0646\u062a\u062c:"}),

        ("product_detail", "text", "bot",
         "{emoji} <b>PRODUCT</b>\n\n"
         "{emoji} {product_name}\n"
         "\U0001f4dd Description: {description}\n\n"
         "\U0001f4b2 Price USD: <b>${price_usd}</b>\n"
         "{stock_emoji} Stock: <b>{stock}</b>\n\n"
         "\U0001f4ca Sold: {sold}\n"
         "{bonus_text}\n"
         "\U0001f6d2 Enter quantity ({stock}-{stock}):",
         {"ar": "{emoji} <b>{product_name}</b>\n"
          "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
          "\U0001f4dd {description}\n\n"
          "\U0001f4b2 <b>\u0627\u0644\u0633\u0639\u0631:</b> ${price_usd}\n"
          "\U0001f4e6 <b>\u0627\u0644\u0645\u062e\u0632\u0648\u0646:</b> {stock_emoji} {stock}\n"
          "\U0001f4ca <b>\u0627\u0644\u0645\u0628\u0627\u0639:</b> {sold}\n"
          "{bonus_text}\n\n"
          "\U0001f6d2 \u0627\u0636\u063a\u0637 <b>\u0627\u0634\u062a\u0631\u064a \u0627\u0644\u0622\u0646</b> \u0644\u0644\u0634\u0631\u0627\u0621"}),

        ("order_summary", "text", "bot",
         "\U0001f9fe <b>Order Summary</b>\n"
         "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
         "{emoji} <b>Product:</b> {product_name}\n"
         "{description}"
         "\U0001f4b2 <b>Unit Price:</b> ${unit_price}\n"
         "\U0001f4e6 <b>Quantity:</b> {qty}\n"
         "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
         "\U0001f4b0 <b>Total:</b> ${total_usd}\n"
         "\U0001f194 <b>Order:</b> <code>{order_number}</code>\n"
         "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
         "\U0001f39f Have a coupon? Tap <b>Use Coupon</b>\n"
         "\U0001f4b3 Or tap <b>Pay Now</b> to proceed",
         {"ar": "\U0001f9fe <b>\u0645\u0644\u062e\u0635 \u0627\u0644\u0637\u0644\u0628</b>\n"
          "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
          "{emoji} <b>\u0627\u0644\u0645\u0646\u062a\u062c:</b> {product_name}\n"
          "{description}"
          "\U0001f4b2 <b>\u0633\u0639\u0631 \u0627\u0644\u0648\u062d\u062f\u0629:</b> ${unit_price}\n"
          "\U0001f4e6 <b>\u0627\u0644\u0643\u0645\u064a\u0629:</b> {qty}\n"
          "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
          "\U0001f4b0 <b>\u0627\u0644\u0625\u062c\u0645\u0627\u0644\u064a:</b> ${total_usd}\n"
          "\U0001f194 <b>\u0631\u0642\u0645 \u0627\u0644\u0637\u0644\u0628:</b> <code>{order_number}</code>\n"
          "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
          "\U0001f39f \u0644\u0648 \u0639\u0646\u062f\u0643 \u0643\u0648\u0628\u0648\u0646 \u062e\u0635\u0645 \u0627\u0636\u063a\u0637 <b>\u0627\u0633\u062a\u062e\u062f\u0627\u0645 \u0643\u0648\u0628\u0648\u0646</b>\n"
          "\U0001f4b3 \u0623\u0648 \u0627\u0636\u063a\u0637 <b>\u0627\u062f\u0641\u0639 \u0627\u0644\u0622\u0646</b> \u0644\u0644\u0645\u062a\u0627\u0628\u0639\u0629"}),

        ("payment_binance", "text", "bot",
         "\U0001f4ab <b>BINANCE INTERNAL TRANSFER</b>\n\n"
         "\U0001f194 Order ID: <b>{order_number}</b>\n"
         "\U0001f4ab Binance UID:\n<code>{wallet_address}</code>\n\n"
         "\U0001f4dd Note:\n<code>{order_number}</code>\n\n"
         "\U0001f4b2 Amount:\n<code>${amount} USDT</code>\n\n"
         "\U0001f4cb <b>Instructions:</b>\n"
         "1. Open Binance \u2192 Send to Binance users (Send via UID)\n"
         "2. Enter the recipient UID: <code>{wallet_address}</code>\n"
         "3. Enter amount: <code>${amount} USDT</code>\n"
         "4. Enter note: <code>{order_number}</code>\n\n"
         "\u26a0\ufe0f You <b>MUST</b> enter the exact <b>NOTE</b> above for auto-confirmation!\n"
         "\u23f0 Order expires in <b>{timeout} minutes</b>.",
         {"ar": "\U0001f4ab <b>\u062a\u062d\u0648\u064a\u0644 \u0628\u064a\u0646\u0627\u0646\u0633 \u0627\u0644\u062f\u0627\u062e\u0644\u064a</b>\n\n"
          "\U0001f194 \u0631\u0642\u0645 \u0627\u0644\u0637\u0644\u0628: <b>{order_number}</b>\n"
          "\U0001f4ab Binance UID:\n<code>{wallet_address}</code>\n\n"
          "\U0001f4dd \u0627\u0644\u0645\u0644\u0627\u062d\u0638\u0629:\n<code>{order_number}</code>\n\n"
          "\U0001f4b2 \u0627\u0644\u0645\u0628\u0644\u063a:\n<code>${amount} USDT</code>\n\n"
          "\u26a0\ufe0f <b>\u064a\u062c\u0628</b> \u0643\u062a\u0627\u0628\u0629 <b>\u0627\u0644\u0645\u0644\u0627\u062d\u0638\u0629</b> \u0628\u0627\u0644\u0636\u0628\u0637 \u0644\u0644\u062a\u0623\u0643\u064a\u062f \u0627\u0644\u062a\u0644\u0642\u0627\u0626\u064a!\n"
          "\u23f0 \u064a\u0646\u062a\u0647\u064a \u0627\u0644\u0637\u0644\u0628 \u062e\u0644\u0627\u0644 <b>{timeout} \u062f\u0642\u064a\u0642\u0629</b>."}),

        ("payment_crypto", "text", "bot",
         "\U0001f48e <b>CRYPTO PAYMENT</b>\n\n"
         "\U0001f194 Order ID: <b>{order_number}</b>\n\n"
         "\U0001f4cb Wallet Address:\n<code>{wallet_address}</code>\n\n"
         "\U0001f4b2 Amount:\n<code>${amount} USDT</code>\n\n"
         "\U0001f4dd Note:\n<code>{order_number}</code>\n\n"
         "\u26a0\ufe0f Send <b>exactly</b> the amount above.\n"
         "\u23f0 Order expires in <b>{timeout} minutes</b>.",
         {"ar": "\U0001f48e <b>\u062f\u0641\u0639 \u0643\u0631\u064a\u0628\u062a\u0648</b>\n\n"
          "\U0001f194 \u0627\u0644\u0637\u0644\u0628: <b>{order_number}</b>\n\n"
          "\U0001f4cb \u0627\u0644\u0639\u0646\u0648\u0627\u0646:\n<code>{wallet_address}</code>\n\n"
          "\U0001f4b2 \u0627\u0644\u0645\u0628\u0644\u063a:\n<code>${amount} USDT</code>\n\n"
          "\u23f0 \u064a\u0646\u062a\u0647\u064a \u0627\u0644\u0637\u0644\u0628 \u062e\u0644\u0627\u0644 <b>{timeout} \u062f\u0642\u064a\u0642\u0629</b>."}),

        ("order_delivered", "text", "bot",
         "\U0001f389 <b>Payment successful!</b>\n"
         "\U0001f6cd <b>Product:</b> {product_name}\n"
         "\U0001f194 <b>Order ID:</b> <code>{order_number}</code>\n\n"
         "\U0001f4c5 <b>Purchase date:</b> {purchase_date}\n"
         "{note}"
         "\n{delivery_items}\n\n"
         "Thank you for your purchase \u2764\ufe0f Type /products to see the items you need!!!",
         {"ar": "\U0001f389 <b>\u062a\u0645 \u0627\u0644\u062f\u0641\u0639 \u0628\u0646\u062c\u0627\u062d!</b>\n"
          "\U0001f6cd <b>\u0627\u0644\u0645\u0646\u062a\u062c:</b> {product_name}\n"
          "\U0001f194 <b>\u0631\u0642\u0645 \u0627\u0644\u0637\u0644\u0628:</b> <code>{order_number}</code>\n\n"
          "\U0001f4c5 <b>\u062a\u0627\u0631\u064a\u062e \u0627\u0644\u0634\u0631\u0627\u0621:</b> {purchase_date}\n"
          "{note}"
          "\n{delivery_items}\n\n"
          "\u0634\u0643\u0631\u0627\u064b \u0644\u0634\u0631\u0627\u0626\u0643 \u2764\ufe0f \u0627\u0643\u062a\u0628 /products \u0644\u0645\u0634\u0627\u0647\u062f\u0629 \u0627\u0644\u0645\u0646\u062a\u062c\u0627\u062a!!!"}),

        ("delivery_file_caption", "text", "bot",
         "\U0001f389 <b>Payment successful!</b>\n"
         "\U0001f6cd <b>Product:</b> {product_name}\n"
         "\U0001f194 <b>Order ID:</b> <code>{order_number}</code>\n\n"
         "\U0001f4c5 <b>Purchase date:</b> {purchase_date}\n"
         "\U0001f4e6 <b>Delivered accounts:</b> {qty}\n"
         "{note}\n\n"
         "\U0001f4ce <b>Full account list attached above.</b>",
         {"ar": "\U0001f389 <b>\u062a\u0645 \u0627\u0644\u062f\u0641\u0639 \u0628\u0646\u062c\u0627\u062d!</b>\n"
          "\U0001f6cd <b>\u0627\u0644\u0645\u0646\u062a\u062c:</b> {product_name}\n"
          "\U0001f194 <b>\u0631\u0642\u0645 \u0627\u0644\u0637\u0644\u0628:</b> <code>{order_number}</code>\n\n"
          "\U0001f4c5 <b>\u062a\u0627\u0631\u064a\u062e \u0627\u0644\u0634\u0631\u0627\u0621:</b> {purchase_date}\n"
          "\U0001f4e6 <b>\u0627\u0644\u062d\u0633\u0627\u0628\u0627\u062a \u0627\u0644\u0645\u0633\u0644\u0645\u0629:</b> {qty}\n"
          "{note}\n\n"
          "\U0001f4ce <b>\u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u062d\u0633\u0627\u0628\u0627\u062a \u0627\u0644\u0643\u0627\u0645\u0644\u0629 \u0628\u0627\u0644\u0623\u0639\u0644\u0649.</b>"}),

        ("payment_confirmed_auto", "text", "bot",
         "\u2705 <b>Payment Confirmed!</b>\n\n"
         "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
         "\U0001f194 Order: <b>{order_number}</b>\n"
         "\U0001f4b2 Amount: <b>${amount}</b>\n\n"
         "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
         "\u23f3 Your order is being processed...",
         {"ar": "\u2705 <b>\u062a\u0645 \u062a\u0623\u0643\u064a\u062f \u0627\u0644\u062f\u0641\u0639!</b>\n\n"
          "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
          "\U0001f194 \u0627\u0644\u0637\u0644\u0628: <b>{order_number}</b>\n"
          "\U0001f4b2 \u0627\u0644\u0645\u0628\u0644\u063a: <b>${amount}</b>\n\n"
          "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
          "\u23f3 \u062c\u0627\u0631\u064a \u062a\u062c\u0647\u064a\u0632 \u0637\u0644\u0628\u0643..."}),

        ("notify_admin_deposit", "text", "bot",
         "\u2705 <b>Deposit Received!</b>\n\n"
         "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
         "\U0001f4b0 Amount: <b>+${amount}</b>\n"
         "\U0001f4b5 New Balance: <b>${balance}</b>\n"
         "\U0001f4dd Note: {note}\n\n"
         "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
         "\U0001f6cd You can now use your balance to purchase from the store!",
         {"ar": "\u2705 <b>\u062a\u0645 \u0625\u064a\u062f\u0627\u0639 \u0631\u0635\u064a\u062f!</b>\n\n"
          "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
          "\U0001f4b0 \u0627\u0644\u0645\u0628\u0644\u063a: <b>+${amount}</b>\n"
          "\U0001f4b5 \u0627\u0644\u0631\u0635\u064a\u062f \u0627\u0644\u062c\u062f\u064a\u062f: <b>${balance}</b>\n"
          "\U0001f4dd \u0645\u0644\u0627\u062d\u0638\u0629: {note}\n\n"
          "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
          "\U0001f6cd \u064a\u0645\u0643\u0646\u0643 \u0627\u0644\u0622\u0646 \u0627\u0633\u062a\u062e\u062f\u0627\u0645 \u0631\u0635\u064a\u062f\u0643 \u0644\u0644\u0634\u0631\u0627\u0621 \u0645\u0646 \u0627\u0644\u0645\u062a\u062c\u0631!"}),

        ("notify_deposit_approved", "text", "bot",
         "\u2705 <b>Deposit Confirmed!</b>\n\n"
         "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
         "\U0001f4b0 Amount: <b>+${amount}</b>\n"
         "\U0001f4b3 Method: {method}\n"
         "\U0001f4b5 New Balance: <b>${balance}</b>\n"
         "\U0001f194 Ref: <code>{reference}</code>\n\n"
         "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
         "\U0001f6cd Your balance has been updated! Start shopping now.",
         {"ar": "\u2705 <b>\u062a\u0645 \u062a\u0623\u0643\u064a\u062f \u0627\u0644\u0625\u064a\u062f\u0627\u0639!</b>\n\n"
          "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
          "\U0001f4b0 \u0627\u0644\u0645\u0628\u0644\u063a: <b>+${amount}</b>\n"
          "\U0001f4b3 \u0627\u0644\u0637\u0631\u064a\u0642\u0629: {method}\n"
          "\U0001f4b5 \u0627\u0644\u0631\u0635\u064a\u062f \u0627\u0644\u062c\u062f\u064a\u062f: <b>${balance}</b>\n"
          "\U0001f194 \u0627\u0644\u0645\u0631\u062c\u0639: <code>{reference}</code>\n\n"
          "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
          "\U0001f6cd \u062a\u0645 \u062a\u062d\u062f\u064a\u062b \u0631\u0635\u064a\u062f\u0643! \u0627\u0628\u062f\u0623 \u0627\u0644\u062a\u0633\u0648\u0642 \u0627\u0644\u0622\u0646."}),

        ("notify_deposit_rejected", "text", "bot",
         "\u274c <b>Deposit Rejected</b>\n\n"
         "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
         "\U0001f4b0 Amount: ${amount}\n"
         "\U0001f4b3 Method: {method}\n"
         "\U0001f194 Ref: <code>{reference}</code>\n\n"
         "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
         "\U0001f4e9 Please contact support if you believe this is an error.",
         {"ar": "\u274c <b>\u062a\u0645 \u0631\u0641\u0636 \u0627\u0644\u0625\u064a\u062f\u0627\u0639</b>\n\n"
          "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
          "\U0001f4b0 \u0627\u0644\u0645\u0628\u0644\u063a: ${amount}\n"
          "\U0001f4b3 \u0627\u0644\u0637\u0631\u064a\u0642\u0629: {method}\n"
          "\U0001f194 \u0627\u0644\u0645\u0631\u062c\u0639: <code>{reference}</code>\n\n"
          "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
          "\U0001f4e9 \u062a\u0648\u0627\u0635\u0644 \u0645\u0639 \u0627\u0644\u062f\u0639\u0645 \u0625\u0630\u0627 \u0643\u0646\u062a \u062a\u0639\u062a\u0642\u062f \u0623\u0646 \u0647\u0630\u0627 \u062e\u0637\u0623."}),

        ("notify_order_delivered", "text", "bot",
         "\u2705 <b>Order #{order_number} \u2014 Delivered!</b>\n\n"
         "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
         "{delivery_items}\n\n"
         "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
         "\U0001f4b0 Total: <b>${total}</b>\n\n"
         "\u26a0\ufe0f <b>Save this data!</b> It will not be shown again.\n\n"
         "Thank you for shopping! \U0001f389",
         {"ar": "\u2705 <b>\u0637\u0644\u0628 #{order_number} \u2014 \u062a\u0645 \u0627\u0644\u062a\u0633\u0644\u064a\u0645!</b>\n\n"
          "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
          "{delivery_items}\n\n"
          "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
          "\U0001f4b0 \u0627\u0644\u0625\u062c\u0645\u0627\u0644\u064a: <b>${total}</b>\n\n"
          "\u26a0\ufe0f <b>\u0627\u062d\u0641\u0638 \u0647\u0630\u0647 \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a!</b> \u0644\u0646 \u062a\u0638\u0647\u0631 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649.\n\n"
          "\u0634\u0643\u0631\u0627\u064b \u0644\u062a\u0633\u0648\u0642\u0643! \U0001f389"}),

        ("notify_order_rejected", "text", "bot",
         "\u274c <b>Order #{order_number} \u2014 Rejected</b>\n\n"
         "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
         "\U0001f4dd Reason: {reason}\n\n"
         "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
         "\U0001f4e9 Contact support if you have questions.",
         {"ar": "\u274c <b>\u0637\u0644\u0628 #{order_number} \u2014 \u0645\u0631\u0641\u0648\u0636</b>\n\n"
          "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
          "\U0001f4dd \u0627\u0644\u0633\u0628\u0628: {reason}\n\n"
          "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
          "\U0001f4e9 \u062a\u0648\u0627\u0635\u0644 \u0645\u0639 \u0627\u0644\u062f\u0639\u0645 \u0644\u0623\u064a \u0627\u0633\u062a\u0641\u0633\u0627\u0631."}),

        ("notify_balance_deducted", "text", "bot",
         "\U0001f4e4 <b>Balance Updated</b>\n\n"
         "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
         "\U0001f4b0 Deducted: <b>-${amount}</b>\n"
         "\U0001f4b5 New Balance: <b>${balance}</b>\n"
         "\U0001f4dd Reason: {note}\n\n"
         "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501",
         {"ar": "\U0001f4e4 <b>\u062a\u062d\u062f\u064a\u062b \u0627\u0644\u0631\u0635\u064a\u062f</b>\n\n"
          "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
          "\U0001f4b0 \u062a\u0645 \u062e\u0635\u0645: <b>-${amount}</b>\n"
          "\U0001f4b5 \u0627\u0644\u0631\u0635\u064a\u062f \u0627\u0644\u062c\u062f\u064a\u062f: <b>${balance}</b>\n"
          "\U0001f4dd \u0627\u0644\u0633\u0628\u0628: {note}\n\n"
          "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501"}),
    ]

    for key, mtype, group, content, i18n in default_messages:
        exists = (await session.execute(
            select(MessageTemplate).where(MessageTemplate.key == key)
        )).scalar_one_or_none()
        if not exists:
            session.add(MessageTemplate(
                key=key, type=mtype, content=content,
                content_i18n=i18n, group=group, is_active=True,
            ))
            inserted += 1
            print(f"    + Template: {key}")

    # 4. Payment methods
    payment_methods = [
        ("binance_uid", "Binance Pay (UID)", "crypto", 1),
        ("usdt_trc20", "USDT (TRC20)", "crypto", 2),
        ("usdt_bep20", "USDT/USDC (BSC)", "crypto", 3),
        ("wallet", "Wallet Balance", "internal", 10),
    ]
    for code, name, ptype, sort in payment_methods:
        exists = (await session.execute(
            select(PaymentMethod).where(PaymentMethod.code == code)
        )).scalar_one_or_none()
        if not exists:
            session.add(PaymentMethod(name=name, code=code, type=ptype, is_enabled=True, sort_order=sort))
            print(f"    + Payment: {code}")

    # 5. Default delivery rule
    exists = (await session.execute(
        select(DeliveryRule).where(DeliveryRule.is_default == True)
    )).scalar_one_or_none()
    if not exists:
        session.add(DeliveryRule(
            name="Auto Delivery", mode="auto",
            template="\U0001f4e6 Here's your order:\n\n{delivery_data}",
            is_default=True,
        ))
        print("    + Delivery: Auto Delivery rule")

    await session.commit()
    print(f"    Seed complete! ({inserted} new templates inserted)")


if __name__ == "__main__":
    asyncio.run(main())
