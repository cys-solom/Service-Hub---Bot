# -*- coding: utf-8 -*-
"""Store settings service — reads from DB, falls back to .env config."""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
from models.system import AppSetting

logger = logging.getLogger(__name__)


async def get_setting(session: AsyncSession, key: str, fallback: str = "") -> str:
    """Get a store setting from DB, fallback to provided value."""
    try:
        row = (await session.execute(
            select(AppSetting).where(AppSetting.key == key, AppSetting.is_deleted == False)
        )).scalar_one_or_none()
        if row and row.value:
            return row.value
    except Exception as e:
        logger.warning(f"[store_settings] DB read failed for '{key}': {e}")
    return fallback


async def get_store_vars(session: AsyncSession, config) -> dict:
    """
    Return all common store variables for CMS template rendering.
    Reads from DB first; falls back to .env config values.
    """
    support_user  = await get_setting(session, "support_user",  config.SUPPORT_USERNAME or "@admin")
    store_name    = await get_setting(session, "store_name",    config.STORE_NAME or "Diaa Store")
    channel_url   = await get_setting(session, "channel_url",   config.CHANNEL_URL or "https://t.me/")
    pay_timeout   = await get_setting(session, "payment_timeout", str(getattr(config, "PAYMENT_TIMEOUT_MINUTES", 30)))

    return {
        "support_user":   support_user,
        "store_name":     store_name,
        "channel_url":    channel_url,
        "payment_timeout": pay_timeout,
    }
