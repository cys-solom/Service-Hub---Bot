"""i18n middleware — sets user language in handler data"""
from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy import select

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
from models.user import User


class I18nMiddleware(BaseMiddleware):
    async def __call__(
        self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject, data: dict[str, Any],
    ) -> Any:
        session = data.get("session")
        user = event.from_user if hasattr(event, 'from_user') else None
        lang = "en"

        if session and user:
            result = await session.execute(
                select(User.language_code).where(User.telegram_id == user.id)
            )
            db_lang = result.scalar_one_or_none()
            if db_lang:
                lang = db_lang

        data["lang"] = lang
        return await handler(event, data)
