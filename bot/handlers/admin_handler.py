"""Admin commands handler — /broadcast, /ban, /stats, /admin"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
from models.user import User
from models.order import Order
from models.stock import StockItem
from models.catalog import Product
from models.support import SupportTicket
from models.wallet import Wallet

from config import settings

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids_list


# ─── /admin — Quick stats dashboard ─────────────────
@router.message(Command("admin"))
async def admin_panel(message: Message, session: AsyncSession, **kwargs):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Access denied")
        return

    total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
    total_orders = (await session.execute(select(func.count(Order.id)))).scalar() or 0
    pending = (await session.execute(
        select(func.count(Order.id)).where(Order.status.in_(["pending", "waiting_payment", "under_review"]))
    )).scalar() or 0
    stock = (await session.execute(
        select(func.count(StockItem.id)).where(StockItem.is_sold == False, StockItem.is_deleted == False)
    )).scalar() or 0
    revenue = (await session.execute(
        select(func.coalesce(func.sum(Order.final_amount), 0)).where(Order.status == "delivered")
    )).scalar() or 0
    open_tickets = (await session.execute(
        select(func.count(SupportTicket.id)).where(SupportTicket.status.in_(["open", "in_progress"]))
    )).scalar() or 0

    text = (
        f"🔑 <b>Admin Dashboard</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Users: <b>{total_users}</b>\n"
        f"📦 Total Orders: <b>{total_orders}</b>\n"
        f"⏳ Pending: <b>{pending}</b>\n"
        f"📋 Stock: <b>{stock}</b> items\n"
        f"💰 Revenue: <b>${round(float(revenue), 2)}</b>\n"
        f"🆘 Open Tickets: <b>{open_tickets}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>Admin Commands:</b>\n"
        f"📢 /broadcast — Send message to all users\n"
        f"🚫 /ban — Ban/unban a user\n"
        f"📊 /stats — Detailed statistics\n"
        f"✏️ /editmsg — Edit bot messages\n"
    )

    await message.answer(text)


# ─── /stats — Detailed statistics ────────────────────
@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession, **kwargs):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Access denied")
        return

    # Users stats
    total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
    banned_users = (await session.execute(
        select(func.count(User.id)).where(User.is_banned == True)
    )).scalar() or 0

    # Time-based user stats
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    today_users = (await session.execute(
        select(func.count(User.id)).where(User.created_at >= today_start)
    )).scalar() or 0
    week_users = (await session.execute(
        select(func.count(User.id)).where(User.created_at >= week_ago)
    )).scalar() or 0
    month_users = (await session.execute(
        select(func.count(User.id)).where(User.created_at >= month_ago)
    )).scalar() or 0

    # Order stats
    total_orders = (await session.execute(select(func.count(Order.id)))).scalar() or 0
    delivered = (await session.execute(
        select(func.count(Order.id)).where(Order.status == "delivered")
    )).scalar() or 0
    pending = (await session.execute(
        select(func.count(Order.id)).where(Order.status.in_(["pending", "waiting_payment", "under_review"]))
    )).scalar() or 0
    canceled = (await session.execute(
        select(func.count(Order.id)).where(Order.status == "canceled")
    )).scalar() or 0

    today_orders = (await session.execute(
        select(func.count(Order.id)).where(Order.created_at >= today_start)
    )).scalar() or 0

    # Revenue
    total_revenue = (await session.execute(
        select(func.coalesce(func.sum(Order.final_amount), 0)).where(Order.status == "delivered")
    )).scalar() or 0
    today_revenue = (await session.execute(
        select(func.coalesce(func.sum(Order.final_amount), 0)).where(
            Order.status == "delivered", Order.created_at >= today_start
        )
    )).scalar() or 0

    # Stock
    total_stock = (await session.execute(
        select(func.count(StockItem.id)).where(StockItem.is_sold == False, StockItem.is_deleted == False)
    )).scalar() or 0
    sold_stock = (await session.execute(
        select(func.count(StockItem.id)).where(StockItem.is_sold == True, StockItem.is_deleted == False)
    )).scalar() or 0

    # Products
    total_products = (await session.execute(
        select(func.count(Product.id)).where(Product.is_deleted == False)
    )).scalar() or 0

    # Wallets
    total_balance = (await session.execute(
        select(func.coalesce(func.sum(Wallet.balance), 0))
    )).scalar() or 0
    total_deposited = (await session.execute(
        select(func.coalesce(func.sum(Wallet.total_deposited), 0))
    )).scalar() or 0

    text = (
        f"📊 <b>Detailed Statistics</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Users</b>\n"
        f"   Total: <b>{total_users}</b>\n"
        f"   Today: <b>{today_users}</b>\n"
        f"   This Week: <b>{week_users}</b>\n"
        f"   This Month: <b>{month_users}</b>\n"
        f"   Banned: <b>{banned_users}</b>\n\n"
        f"📦 <b>Orders</b>\n"
        f"   Total: <b>{total_orders}</b>\n"
        f"   Today: <b>{today_orders}</b>\n"
        f"   ✅ Delivered: <b>{delivered}</b>\n"
        f"   ⏳ Pending: <b>{pending}</b>\n"
        f"   ❌ Canceled: <b>{canceled}</b>\n\n"
        f"💰 <b>Revenue</b>\n"
        f"   Total: <b>${round(float(total_revenue), 2)}</b>\n"
        f"   Today: <b>${round(float(today_revenue), 2)}</b>\n\n"
        f"💳 <b>Wallets</b>\n"
        f"   Total Balance: <b>${round(float(total_balance), 2)}</b>\n"
        f"   Total Deposited: <b>${round(float(total_deposited), 2)}</b>\n\n"
        f"📋 <b>Inventory</b>\n"
        f"   Products: <b>{total_products}</b>\n"
        f"   Stock Available: <b>{total_stock}</b>\n"
        f"   Stock Sold: <b>{sold_stock}</b>\n"
    )

    await message.answer(text)


# ─── /broadcast — Send to all users ──────────────────
class BroadcastState(StatesGroup):
    waiting_message = State()


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext, session: AsyncSession, **kwargs):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Access denied")
        return

    # Check if message included inline
    text = message.text.replace("/broadcast", "").strip()
    if text:
        # Direct broadcast
        await _do_broadcast(message, session, text)
        return

    # Ask for message
    total_users = (await session.execute(
        select(func.count(User.telegram_id)).where(User.is_banned == False, User.is_deleted == False)
    )).scalar() or 0

    await message.answer(
        f"📢 <b>Broadcast</b>\n\n"
        f"👥 Will send to <b>{total_users}</b> active users.\n\n"
        f"Send the message you want to broadcast.\n"
        f"Supports: text, photos, stickers.\n\n"
        f"Send /cancel to abort."
    )
    await state.set_state(BroadcastState.waiting_message)


@router.message(BroadcastState.waiting_message, Command("cancel"))
async def cancel_broadcast(message: Message, state: FSMContext, **kwargs):
    await state.clear()
    await message.answer("❌ Broadcast canceled.")


@router.message(BroadcastState.waiting_message)
async def process_broadcast(message: Message, state: FSMContext, session: AsyncSession, **kwargs):
    await state.clear()

    if message.photo:
        # Photo broadcast
        await _do_broadcast_photo(message, session, message.photo[-1].file_id, message.caption or "")
    elif message.text:
        await _do_broadcast(message, session, message.text)
    else:
        await message.answer("❌ Unsupported message type. Send text or a photo.")


async def _do_broadcast(message: Message, session: AsyncSession, text: str):
    users = (await session.execute(
        select(User.telegram_id).where(User.is_banned == False, User.is_deleted == False)
    )).scalars().all()

    status_msg = await message.answer(f"📢 Broadcasting to {len(users)} users...")
    sent, failed, blocked = 0, 0, 0

    for tg_id in users:
        try:
            await message.bot.send_message(tg_id, text, parse_mode="HTML")
            sent += 1
        except Exception as e:
            err = str(e).lower()
            if "blocked" in err or "deactivated" in err:
                blocked += 1
            else:
                failed += 1

        # Progress update every 50 users
        if (sent + failed + blocked) % 50 == 0:
            try:
                await status_msg.edit_text(
                    f"📢 Broadcasting... {sent + failed + blocked}/{len(users)}\n"
                    f"✅ {sent} | ❌ {failed} | 🚫 {blocked}"
                )
            except Exception:
                pass

    await status_msg.edit_text(
        f"📢 <b>Broadcast Complete!</b>\n\n"
        f"📨 Total: <b>{len(users)}</b>\n"
        f"✅ Sent: <b>{sent}</b>\n"
        f"❌ Failed: <b>{failed}</b>\n"
        f"🚫 Blocked/Deactivated: <b>{blocked}</b>"
    )


async def _do_broadcast_photo(message: Message, session: AsyncSession, file_id: str, caption: str):
    users = (await session.execute(
        select(User.telegram_id).where(User.is_banned == False, User.is_deleted == False)
    )).scalars().all()

    status_msg = await message.answer(f"📢 Broadcasting photo to {len(users)} users...")
    sent, failed, blocked = 0, 0, 0

    for tg_id in users:
        try:
            await message.bot.send_photo(tg_id, photo=file_id, caption=caption, parse_mode="HTML")
            sent += 1
        except Exception as e:
            err = str(e).lower()
            if "blocked" in err or "deactivated" in err:
                blocked += 1
            else:
                failed += 1

    await status_msg.edit_text(
        f"📢 <b>Photo Broadcast Complete!</b>\n\n"
        f"📨 Total: <b>{len(users)}</b>\n"
        f"✅ Sent: <b>{sent}</b>\n"
        f"❌ Failed: <b>{failed}</b>\n"
        f"🚫 Blocked: <b>{blocked}</b>"
    )


# ─── /ban — Ban/Unban user ───────────────────────────
class BanState(StatesGroup):
    waiting_user_id = State()


@router.message(Command("ban"))
async def cmd_ban(message: Message, state: FSMContext, session: AsyncSession, **kwargs):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Access denied")
        return

    args = message.text.replace("/ban", "").strip()

    if args:
        # Direct: /ban 123456789
        await _toggle_ban(message, session, args)
        return

    await message.answer(
        "🚫 <b>Ban/Unban User</b>\n\n"
        "Send the user's Telegram ID.\n"
        "If banned → will unban. If active → will ban.\n\n"
        "Send /cancel to abort."
    )
    await state.set_state(BanState.waiting_user_id)


@router.message(BanState.waiting_user_id, Command("cancel"))
async def cancel_ban(message: Message, state: FSMContext, **kwargs):
    await state.clear()
    await message.answer("❌ Canceled.")


@router.message(BanState.waiting_user_id)
async def process_ban(message: Message, state: FSMContext, session: AsyncSession, **kwargs):
    await state.clear()
    await _toggle_ban(message, session, message.text.strip())


async def _toggle_ban(message: Message, session: AsyncSession, user_id_str: str):
    try:
        tg_id = int(user_id_str)
    except ValueError:
        await message.answer("❌ Invalid user ID. Must be a number.")
        return

    user = (await session.execute(
        select(User).where(User.telegram_id == tg_id)
    )).scalar_one_or_none()

    if not user:
        await message.answer(f"❌ User with ID <code>{tg_id}</code> not found.")
        return

    # Toggle ban
    user.is_banned = not user.is_banned
    await session.commit()

    if user.is_banned:
        text = (
            f"🚫 <b>User Banned!</b>\n\n"
            f"👤 Name: <b>{user.first_name or ''} {user.last_name or ''}</b>\n"
            f"🆔 ID: <code>{user.telegram_id}</code>\n"
            f"📛 Username: @{user.username or 'N/A'}\n\n"
            f"Use /ban {tg_id} again to unban."
        )
        # Notify the user
        try:
            await message.bot.send_message(tg_id, "⛔ Your account has been suspended by admin.")
        except Exception:
            pass
    else:
        text = (
            f"✅ <b>User Unbanned!</b>\n\n"
            f"👤 Name: <b>{user.first_name or ''} {user.last_name or ''}</b>\n"
            f"🆔 ID: <code>{user.telegram_id}</code>\n"
            f"📛 Username: @{user.username or 'N/A'}"
        )
        try:
            await message.bot.send_message(tg_id, "✅ Your account has been reactivated!")
        except Exception:
            pass

    await message.answer(text)


# ─── /api_test — Read-only Reseller API health check ─
@router.message(Command("api_test"))
async def cmd_api_test(message: Message, **kwargs):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Access denied")
        return

    status_msg = await message.answer("🔄 Testing Reseller API connection...")

    from bot_services import reseller_api
    from bot_services.reseller_api import ResellerAPIError
    import httpx

    results = {
        "balance": None,
        "balance_ok": False,
        "products": None,
        "products_ok": False,
        "rate_limit": {},
        "error": None,
    }

    # ── Step 1: Check balance ──
    try:
        bal_data = await reseller_api.get_balance()
        results["balance"] = bal_data.get("balance")
        results["balance_ok"] = True
        results["rate_limit"] = bal_data.get("rate_limit", {})
    except ResellerAPIError as e:
        results["error"] = f"Balance check failed: {e.message}"
    except httpx.TimeoutException:
        results["error"] = "⏱ Connection timed out (8s)"
    except httpx.ConnectError:
        results["error"] = "🔌 Cannot connect to API server"
    except ValueError as e:
        results["error"] = str(e)
    except Exception as e:
        results["error"] = f"Unexpected error: {type(e).__name__}"

    # ── Step 2: Fetch products (only if balance succeeded) ──
    if results["balance_ok"]:
        try:
            prod_data = await reseller_api.get_products()
            products = prod_data.get("products", [])
            results["products"] = products
            results["products_ok"] = True
            # Update rate limit from latest call
            if prod_data.get("rate_limit"):
                results["rate_limit"] = prod_data["rate_limit"]
        except ResellerAPIError as e:
            results["error"] = f"Products fetch failed: {e.message}"
        except httpx.TimeoutException:
            results["error"] = "⏱ Products request timed out"
        except Exception as e:
            results["error"] = f"Products error: {type(e).__name__}"

    # ── Build response ──
    if results["error"] and not results["balance_ok"]:
        text = (
            f"❌ <b>Reseller API Test Failed</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"⚠️ {results['error']}\n\n"
            f"Check that RESELLER_API_BASE_URL and RESELLER_API_KEY\n"
            f"are correctly set in your .env file."
        )
    else:
        # Balance display
        balance = results["balance"]
        if isinstance(balance, dict):
            bal_display = balance.get("balance", balance)
        else:
            bal_display = balance

        # Products display
        products = results.get("products") or []
        prod_count = len(products)
        first_3 = products[:3]

        prod_lines = []
        for p in first_3:
            p_name = p.get('name', 'Unknown')
            p_id = p.get('id', '?')
            p_price = p.get('price', '?')
            p_stock = p.get('stock', '?')
            prod_lines.append(
                f"   📌 <b>{p_name}</b>\n"
                f"      ID: <code>{p_id}</code>\n"
                f"      💵 ${p_price}  |  📦 Stock: {p_stock}"
            )
        prod_display = "\n\n".join(prod_lines) if prod_lines else "   (none)"

        # Rate limit display
        rl = results.get("rate_limit", {})
        rl_text = ""
        if rl:
            rl_text = f"\n📊 Rate Limit: {rl.get('remaining', '?')}/{rl.get('limit', '?')} remaining"

        status = "✅ Connected" if results["balance_ok"] and results["products_ok"] else "⚠️ Partial"

        text = (
            f"🔌 <b>Reseller API Test</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"Status: <b>{status}</b>\n"
            f"💰 Balance: <b>{bal_display}</b> USDT\n"
            f"📦 Products: <b>{prod_count}</b>\n\n"
        )

        if prod_count > 0:
            text += f"<b>First {min(3, prod_count)} products:</b>\n\n{prod_display}\n"

        if results.get("error"):
            text += f"\n⚠️ {results['error']}\n"

        text += rl_text

    try:
        await status_msg.edit_text(text)
    except Exception:
        await message.answer(text)


# ─── /api_stock — Check stock for a single product ───
@router.message(Command("api_stock"))
async def cmd_api_stock(message: Message, **kwargs):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Access denied")
        return

    # Extract product_id from command args
    args = message.text.replace("/api_stock", "").strip()
    if not args:
        await message.answer(
            "📋 <b>Usage:</b>\n"
            "<code>/api_stock &lt;product_id&gt;</code>\n\n"
            "Example:\n"
            "<code>/api_stock 550e8400-e29b-41d4-a716-446655440000</code>\n\n"
            "Use /api_test first to see available product IDs."
        )
        return

    product_id = args.split()[0]  # Take first word only

    from bot_services import reseller_api
    from bot_services.reseller_api import ResellerAPIError
    import httpx

    try:
        data = await reseller_api.get_stock(product_id)
        stock_info = data.get("stock", {})
        rl = data.get("rate_limit", {})

        # Format stock info safely
        if isinstance(stock_info, dict):
            stock_display = "\n".join(
                f"   {k}: <b>{v}</b>" for k, v in stock_info.items()
                if k not in ("api_key", "key", "secret", "token")
            )
        else:
            stock_display = f"   Stock: <b>{stock_info}</b>"

        rl_text = ""
        if rl:
            rl_text = f"\n📊 Rate Limit: {rl.get('remaining', '?')}/{rl.get('limit', '?')}"

        text = (
            f"📦 <b>Stock Check</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 Product: <code>{product_id}</code>\n\n"
            f"{stock_display}"
            f"{rl_text}"
        )

    except ResellerAPIError as e:
        error_icons = {401: "🔑", 402: "💰", 409: "⚠️", 429: "🚦"}
        icon = error_icons.get(e.status_code, "❌")
        text = (
            f"{icon} <b>Stock Check Failed</b>\n\n"
            f"Product: <code>{product_id}</code>\n"
            f"Error: {e.message}"
        )
    except httpx.TimeoutException:
        text = f"⏱ <b>Timed out</b> checking stock for\n<code>{product_id}</code>"
    except httpx.ConnectError:
        text = "🔌 Cannot connect to Reseller API"
    except ValueError as e:
        text = f"⚙️ Config error: {e}"
    except Exception as e:
        text = f"❌ Unexpected error: {type(e).__name__}"

    await message.answer(text)

