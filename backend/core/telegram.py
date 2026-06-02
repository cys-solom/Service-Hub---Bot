"""Shared Telegram notification helper for the backend."""
import logging
import httpx
from core.config import settings

logger = logging.getLogger(__name__)


async def send_telegram(chat_id: int, text: str) -> bool:
    """Send an HTML message to a Telegram user via Bot API."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.warning("[TG] No TELEGRAM_BOT_TOKEN configured")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                logger.info(f"[TG] ✅ Sent to {chat_id}")
                return True
            else:
                logger.error(f"[TG] ❌ Error: {resp.text}")
                # Fallback: try without parse mode
                payload["parse_mode"] = ""
                resp2 = await client.post(url, json=payload)
                return resp2.status_code == 200
    except Exception as e:
        logger.error(f"[TG] ❌ Failed: {e}")
        return False
