"""Language handler — change display language → goes to menu after selection"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
from models.user import User

from keyboards import language_kb, main_menu_inline_kb, main_menu_reply_kb
from config import settings
from bot_services import cms
from bot_services.store_settings import get_store_vars

router = Router()


@router.message(Command("languages"))
@router.callback_query(F.data == "menu:language")
async def show_language(event, lang: str = "en", **kwargs):
    text = (
        "🌐 <b>Change Language</b>\n\n"
        "Please choose your preferred language:"
    )
    msg = event if isinstance(event, Message) else event.message
    if isinstance(event, CallbackQuery):
        await msg.edit_text(text, reply_markup=language_kb())
        await event.answer()
    else:
        await msg.answer(text, reply_markup=language_kb())


@router.callback_query(F.data.startswith("lang:"))
async def set_language(callback: CallbackQuery, session: AsyncSession, **kwargs):
    new_lang = callback.data.split(":")[1]

    user = (await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )).scalar_one_or_none()

    if user:
        user.language_code = new_lang
        await session.commit()

    # Confirm
    if new_lang == "ar":
        text = "✅ تم تغيير اللغة إلى العربية"
    else:
        text = "✅ Language changed to English"

    await callback.answer(text, show_alert=True)

    # Read store vars from DB (works for both EN and AR)
    sv = await get_store_vars(session, settings)

    bot_info = await callback.bot.get_me()
    menu_text = await cms.render(session, "main_menu", new_lang,
        bot_username=bot_info.username,
        **sv,
    )

    await callback.message.edit_text(
        menu_text,
        reply_markup=await main_menu_inline_kb(new_lang, sv["channel_url"], sv["support_user"]),
    )
