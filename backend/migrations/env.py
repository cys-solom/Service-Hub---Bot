"""Alembic env.py — async migration support"""
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so Alembic detects them
from models.base import Base
from models.user import User
from models.admin import Admin, Role, Permission, RolePermission
from models.catalog import Category, Product, ProductPrice
from models.stock import StockItem, StockType
from models.order import Order, OrderItem
from models.payment import Payment, PaymentMethod
from models.wallet import Wallet, WalletTransaction
from models.coupon import Coupon
from models.referral import Referral
from models.cms import CommandTemplate, MessageTemplate, ButtonTemplate
from models.flow import FlowNode, FlowEdge
from models.delivery import DeliveryRule
from models.support import SupportTicket
from models.provider import ExternalProvider, ProviderProduct, ProviderLog
from models.system import (
    Language, Translation, AppSetting, AuditLog,
    Notification, NotificationLog, MediaFile, Backup
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
