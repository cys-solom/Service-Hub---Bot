# -*- coding: utf-8 -*-
"""Canboso API Client

Read-only + product purchase client for the Canboso Telegram Buyer API.
API key is loaded from environment variables.
"""
import httpx
import logging
import os

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10.0
BASE_URL = "https://canboso.com"


class CanbosoAPIError(Exception):
    """Raised when the Canboso API returns a non-success response."""
    def __init__(self, status_code: int, message: str, raw: dict | None = None):
        self.status_code = status_code
        self.message = message
        self.raw = raw or {}
        super().__init__(f"[{status_code}] {message}")


def _get_api_key() -> str:
    """Load API key from environment variables."""
    # Use user's key as default fallback if not configured in env
    return os.environ.get(
        "CANBOSO_API_KEY", 
        "tgb_23db46174b4230bec948e2916676c4a8ca75a556aee866f1"
    ).strip()


def _build_headers(api_key: str) -> dict:
    """Build headers with x-api-key auth."""
    return {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }


async def get_products() -> dict:
    """Fetch all active products from Canboso API.

    Returns:
        {"products": [...]}
    """
    api_key = _get_api_key()
    url = f"{BASE_URL}/api/telegram-buyer/products"

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.get(url, headers=_build_headers(api_key))

    if resp.status_code != 200:
        logger.error(f"[Canboso API] Failed to fetch products. Code: {resp.status_code}, Body: {resp.text}")
        raise CanbosoAPIError(resp.status_code, f"API Error: {resp.status_code}")

    try:
        data = resp.json()
    except Exception as e:
        raise CanbosoAPIError(resp.status_code, f"Invalid JSON: {e}")

    if not data.get("success", False):
        raise CanbosoAPIError(resp.status_code, data.get("message", "API request failed"))

    return data


async def purchase_product(product_id: str, quantity: int = 1, customer_email: str = None, slot_months: int = None) -> dict:
    """Purchase a product from Canboso API.

    Args:
        product_id: Product ID on Canboso.
        quantity: Number of units.
        customer_email: Required only for ChatGPT Business Slot.
        slot_months: Required only for ChatGPT Business Slot.

    Returns:
        Purchase response JSON.
    """
    api_key = _get_api_key()
    url = f"{BASE_URL}/api/telegram-buyer/purchase"

    payload = {
        "key": api_key,
        "product_id": product_id,
        "quantity": quantity
    }
    
    if customer_email:
        payload["customer_email"] = customer_email
    if slot_months:
        payload["slot_months"] = slot_months

    logger.info(f"[Canboso API] Purchasing product_id={product_id}, qty={quantity}")

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, headers=_build_headers(api_key), json=payload)

    if resp.status_code != 200:
        logger.error(f"[Canboso API] Purchase failed. Code: {resp.status_code}, Body: {resp.text}")
        try:
            err_data = resp.json()
            msg = err_data.get("message", f"API Error: {resp.status_code}")
        except Exception:
            msg = resp.text[:200]
        raise CanbosoAPIError(resp.status_code, msg)

    try:
        data = resp.json()
    except Exception as e:
        raise CanbosoAPIError(resp.status_code, f"Invalid JSON response: {e}")

    if not data.get("success", False):
        raise CanbosoAPIError(resp.status_code, data.get("message", "Purchase rejected"))

    return data
