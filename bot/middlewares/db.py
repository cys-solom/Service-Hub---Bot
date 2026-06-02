"""Database middleware — injects async session into handler data"""
import os
import socket
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from config import settings

# Auto-detect database
db_url = settings.DATABASE_URL
if "supabase" in db_url or ("localhost" not in db_url and "127.0.0.1" not in db_url and "postgresql" in db_url):
    print(f"[BOT-DB] Using Supabase PostgreSQL")
elif "localhost" in db_url or "127.0.0.1" in db_url:
    try:
        s = socket.create_connection(("localhost", 5432), timeout=1)
        s.close()
        print(f"[BOT-DB] Using local PostgreSQL")
    except (ConnectionRefusedError, OSError, socket.timeout):
        current = Path(__file__).resolve()
        for parent in current.parents:
            if (parent / ".env").exists() or (parent / "docker-compose.yml").exists():
                db_path = parent / "backend" / "diaastore.db"
                break
        else:
            db_path = current.parent.parent.parent / "backend" / "diaastore.db"
        db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
        print(f"[BOT-DB] Using SQLite: {db_path}")

engine_kwargs = {}
if "sqlite" in db_url:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
elif "pooler.supabase" in db_url or "supabase" in db_url:
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 5
    engine_kwargs["pool_recycle"] = 3600
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["connect_args"] = {"prepared_statement_cache_size": 0, "statement_cache_size": 0}
else:
    engine_kwargs["pool_size"] = 20
    engine_kwargs["max_overflow"] = 10
    engine_kwargs["pool_recycle"] = 3600

engine = create_async_engine(db_url, **engine_kwargs)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def get_session_context():
    """Context manager for getting a session — used by background tasks"""
    async with SessionLocal() as session:
        yield session


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
        self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject, data: dict[str, Any],
    ) -> Any:
        try:
            async with SessionLocal() as session:
                data["session"] = session
                return await handler(event, data)
        except Exception as e:
            # If DB is unreachable, still allow handlers that don't need it
            import logging
            logging.getLogger(__name__).warning("[DB] Connection failed: %s — running handler without DB", type(e).__name__)
            data["session"] = None
            return await handler(event, data)

