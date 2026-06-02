# -*- coding: utf-8 -*-
"""API Delivery Service — calls external APIs (e.g. Adobe) on order completion."""
import httpx
import json
import logging

logger = logging.getLogger(__name__)


async def call_api(api_config: dict, user_input: str, order_number: str, qty: int = 1) -> dict:
    """
    Unified API caller. Routes to dedicated service per provider,
    or falls back to generic HTTP call.

    api_config fields:
        api_provider   — 'adobe' or '' (generic)
        url            — endpoint URL  (generic)
        method         — GET / POST / PUT  (generic)
        headers        — dict of HTTP headers
        body           — dict body template; {email} and {order_id} are replaced
        success_key    — JSON key to check in response
        success_value  — expected value for success
        result_key     — key whose value to show the customer
        org_id         — Adobe Org ID  (adobe)
        client_id      — Adobe Client ID  (adobe)
        client_secret  — Adobe Client Secret  (adobe)
    """
    provider = api_config.get("api_provider", "")

    # ── Adobe Creative Cloud ──────────────────────────
    if provider == "adobe":
        from bot_services.adobe_api import activate_adobe_user
        return await activate_adobe_user(
            email         = user_input,
            months        = qty,
            org_id        = api_config.get("org_id",        ""),
            client_id     = api_config.get("client_id",     ""),
            client_secret = api_config.get("client_secret", ""),
        )

    # ── Generic HTTP API ──────────────────────────────
    url = api_config.get("url", "").strip()
    if not url:
        return {"success": False, "error": "API URL not configured for this product."}

    method  = api_config.get("method", "POST").upper()
    headers = api_config.get("headers", {})
    timeout = int(api_config.get("timeout", 30))

    # Build body — replace placeholders
    raw_body = json.dumps(api_config.get("body", {}))
    raw_body = raw_body.replace("{email}",    user_input)
    raw_body = raw_body.replace("{input}",    user_input)
    raw_body = raw_body.replace("{order_id}", order_number)
    raw_body = raw_body.replace("{qty}",      str(qty))
    body = json.loads(raw_body)

    success_key   = api_config.get("success_key",   "status")
    success_value = str(api_config.get("success_value", "success"))
    result_key    = api_config.get("result_key")

    logger.info(f"[API Delivery] → {method} {url}  input={user_input}  order={order_number}")

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if method == "GET":
                resp = await client.get(url, params=body, headers=headers)
            elif method == "PUT":
                resp = await client.put(url, json=body, headers=headers)
            else:
                resp = await client.post(url, json=body, headers=headers)

        logger.info(f"[API Delivery] ← {resp.status_code}  body={resp.text[:200]}")

        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}

        if success_key and success_key in data:
            ok = str(data[success_key]) == success_value
        else:
            ok = resp.status_code in (200, 201)

        if result_key and result_key in data:
            result_text = str(data[result_key])
        elif ok:
            result_text = "✅ Activated successfully!"
        else:
            result_text = data.get("message") or data.get("error") or data.get("detail") or str(data)

        return {
            "success": ok,
            "message": result_text,
            "data": data,
            "status_code": resp.status_code,
            "error": None if ok else result_text,
        }

    except httpx.TimeoutException:
        return {"success": False, "error": "⏰ API request timed out. Please contact support."}
    except Exception as e:
        logger.error(f"[API Delivery] Exception: {e}")
        return {"success": False, "error": f"API error: {e}"}
