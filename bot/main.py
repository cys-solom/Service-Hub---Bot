"""Diaa Store Bot — Main entry point (Aiogram 3) — Full featured"""
import asyncio
import logging
import sys
import os

# Add bot directory first (so bot/services takes priority over backend/services)
_bot_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.join(os.path.dirname(_bot_dir), "backend")
sys.path.insert(0, _bot_dir)
sys.path.insert(1, _backend_dir)

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from middlewares.db import DatabaseMiddleware, SessionLocal
from middlewares.throttle import ThrottleMiddleware
from middlewares.i18n import I18nMiddleware
from handlers import start, catalog, cart, wallet, orders, language, admin_handler, cms_editor, support

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())

    # Middlewares
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    dp.message.middleware(ThrottleMiddleware(rate_limit=1))
    dp.message.middleware(I18nMiddleware())
    dp.callback_query.middleware(I18nMiddleware())

    # Register routers (order matters — commands first, FSM-based editors last)
    dp.include_router(start.router)
    dp.include_router(catalog.router)
    dp.include_router(cart.router)
    dp.include_router(wallet.router)
    dp.include_router(orders.router)
    dp.include_router(language.router)
    dp.include_router(admin_handler.router)
    dp.include_router(support.router)
    dp.include_router(cms_editor.router)  # CMS editor LAST (FSM states don't block other handlers)

    # Set bot commands
    from aiogram.types import BotCommand
    await bot.set_my_commands([
        BotCommand(command="start", description="About Diaa Store"),
        BotCommand(command="menu", description="Main menu - القائمة الرئيسية"),
        BotCommand(command="products", description="Product list - قائمة المنتجات"),
        BotCommand(command="deposit", description="Top Up - شحن"),
        BotCommand(command="wallet", description="Wallet balance - الرصيد"),
        BotCommand(command="myorders", description="Order history - سجل الطلبات"),
        BotCommand(command="languages", description="Change Language - تغيير اللغة"),
        BotCommand(command="support", description="Send Ticket - إرسال تذكرة"),
    ])

    # Start Binance payment checker (if configured)
    binance_task = None
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(_bot_dir), ".env"))
    binance_key = os.environ.get("BINANCE_API_KEY", "")
    binance_secret = os.environ.get("BINANCE_API_SECRET", "")
    binance_uid = os.environ.get("BINANCE_UID", "")

    if binance_key and binance_secret:
        from bot_services.binance_checker import BinanceChecker
        from middlewares.db import get_session_context
        checker = BinanceChecker(binance_key, binance_secret, binance_uid)
        binance_task = asyncio.create_task(
            checker.poll_pending_payments(get_session_context, bot)
        )
        logger.info("[Binance] Auto-verification enabled!")
    else:
        logger.info("[Binance] Not configured — add BINANCE_API_KEY + BINANCE_API_SECRET to .env")

    # Initialize admin notification service
    from bot_services import admin_notify
    admin_group_id = os.environ.get("ADMIN_GROUP_ID", "")
    admin_notify.init(bot, admin_group_id)

    logger.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
