# -*- coding: utf-8 -*-
"""VEX Reseller API Client

Read-only + order placement client for the VEX Reseller API.
API key is loaded exclusively from environment variables.

WARNING: place_order() is implemented but must NOT be called
until the full order flow is approved and connected.
"""
import httpx
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Timeout for all API calls (seconds)
REQUEST_TIMEOUT = 8.0


class ResellerAPIError(Exception):
    """Raised when the Reseller API returns a non-success response."""

    def __init__(self, status_code: int, message: str, raw: dict | None = None):
        self.status_code = status_code
        self.message = message
        self.raw = raw or {}
        super().__init__(f"[{status_code}] {message}")


def _get_config() -> tuple[str, str]:
    """Load base URL and API key from environment variables.

    Returns:
        (base_url, api_key)

    Raises:
        ValueError if either env var is missing.
    """
    base_url = os.environ.get("RESELLER_API_BASE_URL", "")
    api_key = os.environ.get("RESELLER_API_KEY", "")

    if not base_url:
        raise ValueError("RESELLER_API_BASE_URL is not set in environment variables")
    if not api_key:
        raise ValueError("RESELLER_API_KEY is not set in environment variables")

    return base_url.rstrip("/"), api_key


def _build_headers(api_key: str) -> dict:
    """Build request headers with Bearer auth."""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _parse_error(status_code: int, response: httpx.Response) -> ResellerAPIError:
    """Parse error response into a human-readable ResellerAPIError."""
    try:
        data = response.json()
        message = data.get("error") or data.get("message") or str(data)
    except Exception:
        message = response.text[:200] if response.text else "Unknown error"

    error_map = {
        401: "Invalid or revoked API key",
        402: "Insufficient balance",
        409: "Out of stock or duplicate order",
        429: "Rate limit exceeded — try again later",
    }

    friendly = error_map.get(status_code, message)
    return ResellerAPIError(status_code, friendly, data if 'data' in dir() else {})


def _extract_rate_limit(response: httpx.Response) -> dict:
    """Extract rate limit info from response headers if available."""
    info = {}
    limit = response.headers.get("X-RateLimit-Limit")
    remaining = response.headers.get("X-RateLimit-Remaining")
    if limit is not None:
        info["limit"] = int(limit)
    if remaining is not None:
        info["remaining"] = int(remaining)
    return info


# ─── Read-Only Endpoints ──────────────────────────────


async def get_products() -> dict:
    """Fetch all active products from the Reseller API.

    Returns:
        {"products": [...], "rate_limit": {...}}
    """
    base_url, api_key = _get_config()

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.get(
            base_url,
            params={"action": "products"},
            headers=_build_headers(api_key),
        )

    if resp.status_code != 200:
        raise _parse_error(resp.status_code, resp)

    data = resp.json()
    return {
        "products": data if isinstance(data, list) else data.get("products", data),
        "rate_limit": _extract_rate_limit(resp),
    }


async def get_stock(product_id: str) -> dict:
    """Check stock for a specific product.

    Args:
        product_id: The UUID of the product on the Reseller API.

    Returns:
        {"stock": ..., "rate_limit": {...}}
    """
    base_url, api_key = _get_config()

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.get(
            base_url,
            params={"action": "stock", "product_id": product_id},
            headers=_build_headers(api_key),
        )

    if resp.status_code != 200:
        raise _parse_error(resp.status_code, resp)

    data = resp.json()
    return {
        "stock": data,
        "rate_limit": _extract_rate_limit(resp),
    }


async def get_balance() -> dict:
    """Fetch current USDT balance for the API key.

    Returns:
        {"balance": ..., "rate_limit": {...}}
    """
    base_url, api_key = _get_config()

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.get(
            base_url,
            params={"action": "balance"},
            headers=_build_headers(api_key),
        )

    if resp.status_code != 200:
        raise _parse_error(resp.status_code, resp)

    data = resp.json()
    return {
        "balance": data,
        "rate_limit": _extract_rate_limit(resp),
    }


async def get_orders(limit: int = 50, offset: int = 0) -> dict:
    """Fetch order history for this API key.

    Args:
        limit: Number of orders to return (max 50).
        offset: Pagination offset.

    Returns:
        {"orders": [...], "rate_limit": {...}}
    """
    base_url, api_key = _get_config()

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.get(
            base_url,
            params={"action": "orders", "limit": limit, "offset": offset},
            headers=_build_headers(api_key),
        )

    if resp.status_code != 200:
        raise _parse_error(resp.status_code, resp)

    data = resp.json()
    return {
        "orders": data if isinstance(data, list) else data.get("orders", data),
        "rate_limit": _extract_rate_limit(resp),
    }


# ─── Order Placement (NOT called in this phase) ──────


async def place_order(
    product_id: str,
    quantity: int,
    external_order_id: str,
) -> dict:
    """Place an order on the Reseller API.

    ⚠️ WARNING: This function is implemented for future use.
    Do NOT call it until the full order flow is approved.

    Uses external_order_id for idempotency — safe to retry
    with the same ID without double-charging.

    Args:
        product_id: UUID of the product on the Reseller API.
        quantity: Number of units to order.
        external_order_id: Unique local order identifier for idempotency.

    Returns:
        {
            "status": "delivered",
            "order_id": "VEX-XXXXXXXX",
            "data": "delivered_value",
            "amount": 1.23,
            "idempotent_replay": false,
            "rate_limit": {...}
        }
    """
    base_url, api_key = _get_config()

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.post(
            base_url,
            params={"action": "order"},
            headers=_build_headers(api_key),
            json={
                "product_id": product_id,
                "quantity": quantity,
                "external_order_id": external_order_id,
            },
        )

    if resp.status_code != 200:
        raise _parse_error(resp.status_code, resp)

    data = resp.json()
    data["rate_limit"] = _extract_rate_limit(resp)
    return data
