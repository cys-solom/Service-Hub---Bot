"""Seed default data — admin, roles, languages, settings, message templates"""
import logging
from sqlalchemy import select
from core.database import get_session
from core.security import hash_password
from core.config import settings
from models.admin import Admin, Role, Permission, RolePermission
from models.system import Language, AppSetting
from models.cms import CommandTemplate, MessageTemplate, ButtonTemplate
from models.payment import PaymentMethod
from models.delivery import DeliveryRule

logger = logging.getLogger(__name__)


async def seed_defaults():
    async with get_session() as session:
        # --- Super Admin Role ---
        role = (await session.execute(
            select(Role).where(Role.name == "Super Admin")
        )).scalar_one_or_none()
        if not role:
            role = Role(name="Super Admin", description="Full access", is_super=True)
            session.add(role)
            await session.flush()

        # --- Default Admin ---
        admin = (await session.execute(
            select(Admin).where(Admin.username == settings.ADMIN_USERNAME)
        )).scalar_one_or_none()
        if not admin:
            admin = Admin(
                username=settings.ADMIN_USERNAME,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                display_name="Admin",
                is_active=True,
                role_id=role.id,
            )
            session.add(admin)

        # --- Languages ---
        for code, name, native, rtl, flag in [
            ("en", "English", "English", False, "🇬🇧"),
            ("ar", "Arabic", "العربية", True, "🇸🇦"),
        ]:
            existing = (await session.execute(
                select(Language).where(Language.code == code)
            )).scalar_one_or_none()
            if not existing:
                session.add(Language(
                    code=code, name=name, native_name=native,
                    is_rtl=rtl, is_default=(code == "en"),
                    is_enabled=True, flag_emoji=flag,
                ))

        # --- Default Commands (with category + admin flag) ---
        default_commands = [
            # (command, description, is_admin, category)
            ("start", "Start the bot", False, "navigation"),
            ("menu", "Main menu / القائمة الرئيسية", False, "navigation"),
            ("products", "Product list / قائمة المنتجات", False, "navigation"),
            ("deposit", "Top up wallet / شحن", False, "wallet"),
            ("wallet", "Wallet balance / الرصيد", False, "wallet"),
            ("myorders", "Order history / سجل الطلبات", False, "orders"),
            ("languages", "Change Language / تغيير اللغة", False, "general"),
            ("ref", "Referral program", False, "general"),
            # Admin-only commands
            ("editmsg", "Edit bot messages (CMS)", True, "admin"),
            ("broadcast", "Broadcast message to all users", True, "admin"),
            ("ban", "Ban/unban a user", True, "admin"),
            ("stats", "Bot statistics", True, "admin"),
        ]
        for cmd, desc, is_admin, category in default_commands:
            existing = (await session.execute(
                select(CommandTemplate).where(CommandTemplate.command == cmd)
            )).scalar_one_or_none()
            if not existing:
                session.add(CommandTemplate(
                    command=cmd, description=desc,
                    is_enabled=True, is_admin=is_admin, category=category,
                ))

        # --- Default Message Templates (CMS-editable) ---
        default_messages = [
            ("welcome", "text", "bot",
             "👋 Welcome to <b>{store_name}</b>\n\n"
             "Please choose the display language for the bot.\n"
             "You can change it any time with /languages\n\n"
             "👥 Refer friends and earn <b>5%</b> commission!\n"
             "🔗 {ref_link}",
             {"ar": "👋 مرحباً بك في <b>{store_name}</b>\n\n"
              "اختر لغة العرض للبوت.\n"
              "يمكنك تغييرها في أي وقت من /languages\n\n"
              "👥 شارك الرابط واربح <b>5%</b> عمولة!\n"
              "🔗 {ref_link}"}),

            ("main_menu", "text", "bot",
             "🏪 <b>{store_name}</b>\n\n"
             "🤖 Bot Auto 24/7: @{bot_username}\n"
             "👨‍💼 Admin: {support_user}\n\n"
             "🔗 Join Group: {channel_url}\n\n"
             "<b>Quick commands:</b>\n"
             "🛍 Product list: /products\n"
             "💰 Wallet: /wallet /deposit\n"
             "📦 Order history: /myorders\n"
             "👥 Refer friends: /ref\n"
             "🔑 Stock API: /apikey\n"
             "🎫 Send Ticket: /support\n"
             "📋 Main menu: /menu\n"
             "🌐 Change language: /languages\n\n"
             "📌 Use keyboard below for quick access:",
             {"ar": "🏪 <b>{store_name}</b>\n\n"
              "🤖 بوت 24/7: @{bot_username}\n"
              "👨‍💼 الأدمن: {support_user}\n\n"
              "🔗 انضم للجروب: {channel_url}\n\n"
              "<b>أوامر سريعة:</b>\n"
              "🛍 المنتجات: /products\n"
              "💰 المحفظة: /wallet /deposit\n"
              "📦 الطلبات: /myorders\n"
              "🎫 إرسال تذكرة: /support\n"
              "📋 القائمة: /menu\n"
              "🌐 اللغة: /languages"}),

            ("product_list_header", "text", "bot",
             "📋 <b>PRODUCT LIST - {store_name}</b>",
             {"ar": "📋 <b>قائمة المنتجات - {store_name}</b>"}),

            ("product_list_item", "text", "bot",
             "<b>{index}.</b> {emoji} {product_name}\n"
             "   └ USD: <b>${price_usd}</b> | 📦 Avail: <b>{stock}</b>",
             {"ar": "<b>{index}.</b> {emoji} {product_name}\n"
              "   └ السعر: <b>${price_usd}</b> | 📦 المتاح: <b>{stock}</b>"}),

            ("product_list_footer", "text", "bot",
             "\n💬 Quick commands: /products /wallet /deposit /myorders /menu /languages\n"
             "👨‍💼 Admin contact: {support_user}\n"
             "Choose a product below:",
             {"ar": "\n💬 أوامر سريعة: /products /wallet /deposit /myorders /menu /languages\n"
              "👨‍💼 الأدمن: {support_user}\n"
              "اختر منتج:"}),

            ("product_detail", "text", "bot",
             "{emoji} <b>PRODUCT</b>\n\n"
             "{emoji} {product_name}\n"
             "📝 Description: {description}\n\n"
             "💲 Price USD: <b>${price_usd}</b>\n"
             "{stock_emoji} Stock: <b>{stock}</b>\n\n"
             "📊 Sold: {sold}\n"
             "{bonus_text}\n"
             "🛒 Enter quantity ({stock}-{stock}):",
             {"ar": "{emoji} <b>{product_name}</b>\n"
              "━━━━━━━━━━━━━━━━━━\n\n"
              "📝 {description}\n\n"
              "💲 <b>السعر:</b> ${price_usd}\n"
              "📦 <b>المخزون:</b> {stock_emoji} {stock}\n"
              "📊 <b>المباع:</b> {sold}\n"
              "{bonus_text}\n\n"
              "🛒 اضغط <b>اشتري الآن</b> للشراء"}),

            ("order_summary", "text", "bot",
             "🧾 <b>Order Summary</b>\n"
             "━━━━━━━━━━━━━━━━━━\n\n"
             "{emoji} <b>Product:</b> {product_name}\n"
             "{description}"
             "💲 <b>Unit Price:</b> ${unit_price}\n"
             "📦 <b>Quantity:</b> {qty}\n"
             "━━━━━━━━━━━━━━━━━━\n"
             "💰 <b>Total:</b> ${total_usd}\n"
             "🆔 <b>Order:</b> <code>{order_number}</code>\n"
             "━━━━━━━━━━━━━━━━━━\n\n"
             "🎟 Have a coupon? Tap <b>Use Coupon</b>\n"
             "💳 Or tap <b>Pay Now</b> to proceed",
             {"ar": "🧾 <b>ملخص الطلب</b>\n"
              "━━━━━━━━━━━━━━━━━━\n\n"
              "{emoji} <b>المنتج:</b> {product_name}\n"
              "{description}"
              "💲 <b>سعر الوحدة:</b> ${unit_price}\n"
              "📦 <b>الكمية:</b> {qty}\n"
              "━━━━━━━━━━━━━━━━━━\n"
              "💰 <b>الإجمالي:</b> ${total_usd}\n"
              "🆔 <b>رقم الطلب:</b> <code>{order_number}</code>\n"
              "━━━━━━━━━━━━━━━━━━\n\n"
              "🎟 لو عندك كوبون خصم اضغط <b>استخدام كوبون</b>\n"
              "💳 أو اضغط <b>ادفع الآن</b> للمتابعة"}),

            ("payment_binance", "text", "bot",
             "💫 <b>BINANCE INTERNAL TRANSFER</b>\n\n"
             "🆔 Order ID: <b>{order_number}</b>\n"
             "💫 Binance UID:\n<code>{wallet_address}</code>\n\n"
             "📝 Note:\n<code>{order_number}</code>\n\n"
             "💲 Amount:\n<code>${amount} USDT</code>\n\n"
             "📋 <b>Instructions:</b>\n"
             "1. Open Binance → Send to Binance users (Send via UID)\n"
             "2. Enter the recipient UID: <code>{wallet_address}</code>\n"
             "3. Enter amount: <code>${amount} USDT</code>\n"
             "4. Enter note: <code>{order_number}</code>\n\n"
             "⚠️ You <b>MUST</b> enter the exact <b>NOTE</b> above for auto-confirmation!\n"
             "⏰ Order expires in <b>{timeout} minutes</b>.",
             {"ar": "💫 <b>تحويل بينانس الداخلي</b>\n\n"
              "🆔 رقم الطلب: <b>{order_number}</b>\n"
              "💫 Binance UID:\n<code>{wallet_address}</code>\n\n"
              "📝 الملاحظة:\n<code>{order_number}</code>\n\n"
              "💲 المبلغ:\n<code>${amount} USDT</code>\n\n"
              "⚠️ <b>يجب</b> كتابة <b>الملاحظة</b> بالضبط للتأكيد التلقائي!\n"
              "⏰ ينتهي الطلب خلال <b>{timeout} دقيقة</b>."}),

            ("payment_crypto", "text", "bot",
             "💎 <b>CRYPTO PAYMENT</b>\n\n"
             "🆔 Order ID: <b>{order_number}</b>\n\n"
             "📋 Wallet Address:\n<code>{wallet_address}</code>\n\n"
             "💲 Amount:\n<code>${amount} USDT</code>\n\n"
             "📝 Note:\n<code>{order_number}</code>\n\n"
             "⚠️ Send <b>exactly</b> the amount above.\n"
             "⏰ Order expires in <b>{timeout} minutes</b>.",
             {"ar": "💎 <b>دفع كريبتو</b>\n\n"
              "🆔 الطلب: <b>{order_number}</b>\n\n"
              "📋 العنوان:\n<code>{wallet_address}</code>\n\n"
              "💲 المبلغ:\n<code>${amount} USDT</code>\n\n"
              "⏰ ينتهي الطلب خلال <b>{timeout} دقيقة</b>."}),

            ("order_delivered", "text", "bot",
             "🎉 <b>Payment successful!</b>\n"
             "🛍 <b>Product:</b> {product_name}\n"
             "🆔 <b>Order ID:</b> <code>{order_number}</code>\n\n"
             "📅 <b>Purchase date:</b> {purchase_date}\n"
             "{note}"
             "\n{delivery_items}\n\n"
             "Thank you for your purchase ❤️ Type /products to see the items you need!!!",
             {"ar": "🎉 <b>تم الدفع بنجاح!</b>\n"
              "🛍 <b>المنتج:</b> {product_name}\n"
              "🆔 <b>رقم الطلب:</b> <code>{order_number}</code>\n\n"
              "📅 <b>تاريخ الشراء:</b> {purchase_date}\n"
              "{note}"
              "\n{delivery_items}\n\n"
              "شكراً لشرائك ❤️ اكتب /products لمشاهدة المنتجات!!!"}),

            ("delivery_file_caption", "text", "bot",
             "🎉 <b>Payment successful!</b>\n"
             "🛍 <b>Product:</b> {product_name}\n"
             "🆔 <b>Order ID:</b> <code>{order_number}</code>\n\n"
             "📅 <b>Purchase date:</b> {purchase_date}\n"
             "📦 <b>Delivered accounts:</b> {qty}\n"
             "{note}\n\n"
             "📎 <b>Full account list attached above.</b>",
             {"ar": "🎉 <b>تم الدفع بنجاح!</b>\n"
              "🛍 <b>المنتج:</b> {product_name}\n"
              "🆔 <b>رقم الطلب:</b> <code>{order_number}</code>\n\n"
              "📅 <b>تاريخ الشراء:</b> {purchase_date}\n"
              "📦 <b>الحسابات المسلمة:</b> {qty}\n"
              "{note}\n\n"
              "📎 <b>قائمة الحسابات الكاملة بالأعلى.</b>"}),

            ("payment_confirmed_auto", "text", "bot",
             "✅ <b>Payment Confirmed!</b>\n\n"
             "━━━━━━━━━━━━━━━\n\n"
             "🆔 Order: <b>{order_number}</b>\n"
             "💲 Amount: <b>${amount}</b>\n\n"
             "━━━━━━━━━━━━━━━\n\n"
             "⏳ Your order is being processed...",
             {"ar": "✅ <b>تم تأكيد الدفع!</b>\n\n"
              "━━━━━━━━━━━━━━━\n\n"
              "🆔 الطلب: <b>{order_number}</b>\n"
              "💲 المبلغ: <b>${amount}</b>\n\n"
              "━━━━━━━━━━━━━━━\n\n"
              "⏳ جاري تجهيز طلبك..."}),

            # ─── Admin & Notification Templates ───
            ("notify_admin_deposit", "text", "bot",
             "✅ <b>Deposit Received!</b>\n\n"
             "━━━━━━━━━━━━━━━\n\n"
             "💰 Amount: <b>+${amount}</b>\n"
             "💵 New Balance: <b>${balance}</b>\n"
             "📝 Note: {note}\n\n"
             "━━━━━━━━━━━━━━━\n\n"
             "🛍 You can now use your balance to purchase from the store!",
             {"ar": "✅ <b>تم إيداع رصيد!</b>\n\n"
              "━━━━━━━━━━━━━━━\n\n"
              "💰 المبلغ: <b>+${amount}</b>\n"
              "💵 الرصيد الجديد: <b>${balance}</b>\n"
              "📝 ملاحظة: {note}\n\n"
              "━━━━━━━━━━━━━━━\n\n"
              "🛍 يمكنك الآن استخدام رصيدك للشراء من المتجر!"}),

            ("notify_deposit_approved", "text", "bot",
             "✅ <b>Deposit Confirmed!</b>\n\n"
             "━━━━━━━━━━━━━━━\n\n"
             "💰 Amount: <b>+${amount}</b>\n"
             "💳 Method: {method}\n"
             "💵 New Balance: <b>${balance}</b>\n"
             "🆔 Ref: <code>{reference}</code>\n\n"
             "━━━━━━━━━━━━━━━\n\n"
             "🛍 Your balance has been updated! Start shopping now.",
             {"ar": "✅ <b>تم تأكيد الإيداع!</b>\n\n"
              "━━━━━━━━━━━━━━━\n\n"
              "💰 المبلغ: <b>+${amount}</b>\n"
              "💳 الطريقة: {method}\n"
              "💵 الرصيد الجديد: <b>${balance}</b>\n"
              "🆔 المرجع: <code>{reference}</code>\n\n"
              "━━━━━━━━━━━━━━━\n\n"
              "🛍 تم تحديث رصيدك! ابدأ التسوق الآن."}),

            ("notify_deposit_rejected", "text", "bot",
             "❌ <b>Deposit Rejected</b>\n\n"
             "━━━━━━━━━━━━━━━\n\n"
             "💰 Amount: ${amount}\n"
             "💳 Method: {method}\n"
             "🆔 Ref: <code>{reference}</code>\n\n"
             "━━━━━━━━━━━━━━━\n\n"
             "📩 Please contact support if you believe this is an error.",
             {"ar": "❌ <b>تم رفض الإيداع</b>\n\n"
              "━━━━━━━━━━━━━━━\n\n"
              "💰 المبلغ: ${amount}\n"
              "💳 الطريقة: {method}\n"
              "🆔 المرجع: <code>{reference}</code>\n\n"
              "━━━━━━━━━━━━━━━\n\n"
              "📩 تواصل مع الدعم إذا كنت تعتقد أن هذا خطأ."}),

            ("notify_order_delivered", "text", "bot",
             "✅ <b>Order #{order_number} — Delivered!</b>\n\n"
             "━━━━━━━━━━━━━━━\n\n"
             "{delivery_items}\n\n"
             "━━━━━━━━━━━━━━━\n\n"
             "💰 Total: <b>${total}</b>\n\n"
             "⚠️ <b>Save this data!</b> It will not be shown again.\n\n"
             "Thank you for shopping! 🎉",
             {"ar": "✅ <b>طلب #{order_number} — تم التسليم!</b>\n\n"
              "━━━━━━━━━━━━━━━\n\n"
              "{delivery_items}\n\n"
              "━━━━━━━━━━━━━━━\n\n"
              "💰 الإجمالي: <b>${total}</b>\n\n"
              "⚠️ <b>احفظ هذه البيانات!</b> لن تظهر مرة أخرى.\n\n"
              "شكراً لتسوقك! 🎉"}),

            ("notify_order_rejected", "text", "bot",
             "❌ <b>Order #{order_number} — Rejected</b>\n\n"
             "━━━━━━━━━━━━━━━\n\n"
             "📝 Reason: {reason}\n\n"
             "━━━━━━━━━━━━━━━\n\n"
             "📩 Contact support if you have questions.",
             {"ar": "❌ <b>طلب #{order_number} — مرفوض</b>\n\n"
              "━━━━━━━━━━━━━━━\n\n"
              "📝 السبب: {reason}\n\n"
              "━━━━━━━━━━━━━━━\n\n"
              "📩 تواصل مع الدعم لأي استفسار."}),

            ("notify_balance_deducted", "text", "bot",
             "📤 <b>Balance Updated</b>\n\n"
             "━━━━━━━━━━━━━━━\n\n"
             "💰 Deducted: <b>-${amount}</b>\n"
             "💵 New Balance: <b>${balance}</b>\n"
             "📝 Reason: {note}\n\n"
             "━━━━━━━━━━━━━━━",
             {"ar": "📤 <b>تحديث الرصيد</b>\n\n"
              "━━━━━━━━━━━━━━━\n\n"
              "💰 تم خصم: <b>-${amount}</b>\n"
              "💵 الرصيد الجديد: <b>${balance}</b>\n"
              "📝 السبب: {note}\n\n"
              "━━━━━━━━━━━━━━━"}),
        ]

        for key, mtype, group, content, i18n in default_messages:
            existing = (await session.execute(
                select(MessageTemplate).where(MessageTemplate.key == key)
            )).scalar_one_or_none()
            if not existing:
                session.add(MessageTemplate(
                    key=key, type=mtype, content=content,
                    content_i18n=i18n, group=group,
                ))

        # Note: product_detail template was already migrated to use {emoji}.
        # DO NOT force-update it here — user edits via /editmsg must persist.

        # --- Default Payment Methods ---
        default_payments = [
            ("binance_uid", "Binance Pay (UID)", "crypto", 1),
            ("usdt_trc20", "USDT (TRC20)", "crypto", 2),
            ("usdt_bep20", "USDT/USDC (BSC)", "crypto", 3),
            ("wallet", "Wallet Balance", "internal", 10),
        ]
        for code, name, ptype, sort in default_payments:
            existing = (await session.execute(
                select(PaymentMethod).where(PaymentMethod.code == code)
            )).scalar_one_or_none()
            if not existing:
                session.add(PaymentMethod(
                    name=name, code=code, type=ptype,
                    is_enabled=True, sort_order=sort,
                ))

        # --- Default Delivery Rule ---
        existing = (await session.execute(
            select(DeliveryRule).where(DeliveryRule.is_default == True)
        )).scalar_one_or_none()
        if not existing:
            session.add(DeliveryRule(
                name="Auto Delivery", mode="auto",
                template="📦 Here's your order:\n\n{delivery_data}",
                is_default=True,
            ))

        # --- Store Settings (editable from admin panel) ---
        store_settings = [
            ("support_user",    "@admin",              "store", "Support username shown in bot messages (e.g. @YourHandle)"),
            ("store_name",      "Service Hub",          "store", "Store name shown in bot messages"),
            ("channel_url",     "https://t.me/",       "store", "Telegram channel/group URL"),
            ("payment_timeout", "30",                  "store", "Payment timeout in minutes"),
            # Referral system settings
            ("referral_enabled",            "true",    "referral", "Enable/disable referral system"),
            ("referral_commission_percent", "5",       "referral", "Default commission percent for referrals"),
            ("referral_min_order_amount",   "0",       "referral", "Minimum order amount to earn commission"),
            ("referral_auto_credit",        "true",    "referral", "Auto-credit referrer wallet on order delivery"),
            ("referral_max_invites",        "0",       "referral", "Max invites per user (0 = unlimited)"),
        ]
        for key, default_val, group, desc in store_settings:
            existing = (await session.execute(
                select(AppSetting).where(AppSetting.key == key)
            )).scalar_one_or_none()
            if not existing:
                session.add(AppSetting(
                    key=key, value=default_val,
                    type="string", group=group, description=desc,
                ))

        # --- Default Message Templates ---
        notification_templates = [
            ("notify_stock_added", "notifications",
             "⚡️ <b>New Stock Available!</b>\n"
             "━━━━━━━━━━━━━━━━━━━\n\n"
             "📦  <b>{product_name}</b>\n\n"
             "➕  Added: <b>{added_count}</b> items\n"
             "📊  In Stock: <b>{total_stock}</b> available\n\n"
             "━━━━━━━━━━━━━━━━━━━\n"
             "🛒 <b>Order now before it's gone!</b>"),
            ("notify_product_added", "notifications",
             "🆕 <b>New Product Available!</b>\n"
             "━━━━━━━━━━━━━━━━━━━\n\n"
             "📦  <b>{product_name}</b>\n\n"
             "💰  Price: <b>{price}</b>\n"
             "📝  {description}\n\n"
             "━━━━━━━━━━━━━━━━━━━\n"
             "🛒 <b>Order now from the bot!</b>"),
        ]
        for key, group, content in notification_templates:
            existing = (await session.execute(
                select(MessageTemplate).where(MessageTemplate.key == key)
            )).scalar_one_or_none()
            if not existing:
                session.add(MessageTemplate(
                    key=key, type="text", content=content,
                    parse_mode="HTML", is_active=True, group=group,
                ))

        await session.commit()
