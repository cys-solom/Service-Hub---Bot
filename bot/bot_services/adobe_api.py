# -*- coding: utf-8 -*-
"""Adobe Creative Cloud API Service
Uses Adobe I/O OAuth2 client-credentials to add a user to an Adobe Organization.
"""
import httpx
import logging
import asyncio

logger = logging.getLogger(__name__)

# ─── Adobe endpoints ─────────────────────────────────
IMS_TOKEN_URL = "https://ims-na1.adobelogin.com/ims/token/v3"
UMAPI_BASE    = "https://usermanagement.adobe.io/v2/usermanagement"

# ─── Credentials (from product.meta.api_config) ──────
_token_cache: dict = {}   # {"token": str, "expires_at": float}


async def _get_access_token(client_id: str, client_secret: str) -> str:
    """Get or refresh Adobe IMS access token using Client-Credentials flow."""
    import time
    cached = _token_cache.get(f"{client_id}")
    if cached and cached["expires_at"] > time.time() + 60:
        return cached["token"]

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(IMS_TOKEN_URL, data={
            "grant_type":    "client_credentials",
            "client_id":     client_id,
            "client_secret": client_secret,
            "scope":         "AdobeID,openid,user_management_sdk",
        })

    if resp.status_code != 200:
        raise ValueError(f"Adobe IMS token error {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    token        = data["access_token"]
    expires_in   = int(data.get("expires_in", 3600))
    _token_cache[client_id] = {"token": token, "expires_at": time.time() + expires_in}
    logger.info("[Adobe] 🔑 Got new access token, expires in %ds", expires_in)
    return token


async def _get_product_profile(token: str, client_id: str, org_id: str) -> str:
    """Auto-detect the first Creative Cloud product profile name in the org."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{UMAPI_BASE}/users/{org_id}/1",
                headers={"Authorization": f"Bearer {token}", "X-Api-Key": client_id}
            )
        if resp.status_code == 200:
            users = resp.json().get("users", [])
            for user in users:
                groups = user.get("groups", [])
                if groups:
                    logger.info("[Adobe] Auto-detected profile: %s", groups[0])
                    return groups[0]
    except Exception as e:
        logger.warning("[Adobe] Could not auto-detect profile: %s", e)
    return "Creative Cloud Pro Configuration"  # fallback default


async def activate_adobe_user(
    email:         str,
    months:        int,
    org_id:        str,
    client_id:     str,
    client_secret: str,
    product_profile: str = "",   # optional: override auto-detected profile name
) -> dict:
    """
    Add a user to the Adobe org with a Creative Cloud license.

    Returns:
        {"success": bool, "message": str, "data": dict}
    """
    try:
        token = await _get_access_token(client_id, client_secret)
    except Exception as e:
        logger.error("[Adobe] Token fetch failed: %s", e)
        return {"success": False, "message": f"Auth failed: {e}"}

    # ── Auto-detect product profile if not specified ──
    if not product_profile:
        product_profile = await _get_product_profile(token, client_id, org_id)

    logger.info("[Adobe] Using product profile: %s", product_profile)

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Api-Key":     client_id,
        "Content-Type":  "application/json",
    }

    # ── Adobe UMAPI v2 — correct format ──
    # product must be a STRING (profile name), not an object
    payload = [
        {
            "user":      email,
            "requestID": f"req_{email[:8]}",
            "do": [
                {
                    "addAdobeID": {
                        "email":   email,
                        "country": "US",
                        "option":  "ignoreIfAlreadyExists",
                    }
                },
                {
                    "add": {
                        "product": [product_profile]   # ← string, not object
                    }
                }
            ]
        }
    ]

    url = f"{UMAPI_BASE}/action/{org_id}"
    logger.info("[Adobe] POST %s  email=%s  months=%d  profile=%s", url, email, months, product_profile)

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=headers)

    logger.info("[Adobe] Response %d: %s", resp.status_code, resp.text[:500])

    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}

    # Adobe UMAPI: 200 = queued OK
    if resp.status_code in (200, 201, 204):
        errors = data.get("errors") or []
        if errors:
            err_msg = "; ".join(
                e.get("message", str(e)) for e in errors if isinstance(e, dict)
            ) or str(errors)
            return {"success": False, "message": f"Adobe error: {err_msg}", "data": data}

        return {
            "success": True,
            "message": (
                f"✅ Adobe Creative Cloud activated!\n"
                f"📧 Account: {email}\n"
                f"📅 Duration: {months} month{'s' if months != 1 else ''}\n\n"
                f"Check your email for confirmation from Adobe."
            ),
            "data": data,
        }
    else:
        err = data.get("message") or data.get("error") or resp.text[:200]
        return {"success": False, "message": f"Adobe API error ({resp.status_code}): {err}", "data": data}
