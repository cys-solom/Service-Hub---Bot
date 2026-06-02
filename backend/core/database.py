"""Async SQLAlchemy engine + session factory — Supabase PostgreSQL / SQLite fallback"""
import os
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from core.config import settings

# Database URL resolution
db_url = settings.DATABASE_URL

# If it's a Supabase/remote PostgreSQL URL, use it directly
if "supabase" in db_url or ("localhost" not in db_url and "127.0.0.1" not in db_url and "postgresql" in db_url):
    print(f"[DB] Using remote PostgreSQL (Supabase)")
elif "localhost" in db_url or "127.0.0.1" in db_url:
    # Check if we can connect to local PostgreSQL, otherwise use SQLite
    import socket
    try:
        s = socket.create_connection(("localhost", 5432), timeout=1)
        s.close()
        print(f"[DB] Using local PostgreSQL")
    except (ConnectionRefusedError, OSError, socket.timeout):
        db_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(db_dir, "diaastore.db")
        db_url = f"sqlite+aiosqlite:///{db_path}"
        print(f"[DB] PostgreSQL not available, using SQLite: {db_path}")

# Engine config
engine_kwargs = {
    "echo": settings.DEBUG,
}

if "sqlite" in db_url:
    # SQLite doesn't support pool_size
    engine_kwargs["connect_args"] = {"check_same_thread": False}
elif "pooler.supabase" in db_url or "supabase" in db_url:
    # Supabase pooler requires prepared_statement_cache_size=0
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 5
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["connect_args"] = {"prepared_statement_cache_size": 0, "statement_cache_size": 0}
else:
    engine_kwargs["pool_size"] = 20
    engine_kwargs["max_overflow"] = 10
    engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(db_url, **engine_kwargs)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_session():
    session = async_session_factory()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db() -> AsyncSession:
    """FastAPI dependency"""
    async with get_session() as session:
        yield session
