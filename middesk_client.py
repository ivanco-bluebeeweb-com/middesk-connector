"""Middesk HTTP client -- static Bearer API key auth + REST API v1.
Function-based, `ctx.http`-driven, same shape as DocuSign Connector's
docusign_client.py / CircleCI Connector's circleci_client.py (no raw
httpx.AsyncClient -- SDK's own context-bound HTTP client only). See
app.py's module docstring for the full architectural reasoning behind
BYOK + static key auth.

AUTH (confirmed via docs.middesk.com/build/api-keys, 2026-08-22/23):

No OAuth. A single static API key per environment, sent as
`Authorization: Bearer {api_key}`. Key prefix and base URL must match:
`mk_test_...` keys only work against `api-sandbox.middesk.com`,
`mk_live_...` keys only work against `api.middesk.com`. There is no
token exchange step and nothing to cache -- every request just carries
the stored key directly.
"""
from __future__ import annotations

from typing import Any

SANDBOX_BASE = "https://api-sandbox.middesk.com/v1"
PRODUCTION_BASE = "https://api.middesk.com/v1"

UNAUTHORIZED = "MIDDESK_UNAUTHORIZED"
FORBIDDEN = "MIDDESK_FORBIDDEN"
NOT_FOUND = "MIDDESK_NOT_FOUND"
VALIDATION_FAILED = "MIDDESK_VALIDATION_FAILED"
RESPONSE_UNEXPECTED = "MIDDESK_RESPONSE_UNEXPECTED"
RATE_LIMITED = "MIDDESK_RATE_LIMITED"
BACKEND_5XX = "MIDDESK_BACKEND_5XX"
ENV_KEY_MISMATCH = "MIDDESK_ENV_KEY_MISMATCH"

_MESSAGES = {
    UNAUTHORIZED: "Middesk rejected this API key. Check the key value and environment, then reconnect.",
    FORBIDDEN: "Middesk accepted the key but denied this operation -- the key's account plan may not include this product.",
    NOT_FOUND: "Middesk has no such resource, or this account cannot access it.",
    VALIDATION_FAILED: "Middesk rejected the request as invalid.",
    RESPONSE_UNEXPECTED: "Middesk returned a response the connector could not safely interpret.",
    RATE_LIMITED: "Middesk is rate-limiting requests; try again shortly.",
    BACKEND_5XX: "Middesk returned a server error; try again shortly.",
    ENV_KEY_MISMATCH: "This API key's prefix does not match the selected environment (mk_test_ needs sandbox, mk_live_ needs production).",
}
_RETRYABLE = {RATE_LIMITED, BACKEND_5XX}


def fail(code: str, detail: str = "") -> dict:
    message = _MESSAGES.get(code, code)
    if detail:
        message = f"{message} ({detail})"
    return {"ok": False, "error_code": code, "error": message, "retryable": code in _RETRYABLE}


class ClientFail(Exception):
    def __init__(self, payload: dict):
        super().__init__(payload.get("error", "Middesk request failed"))
        self.payload = payload
        self.message = payload.get("error", "Middesk request failed")


def base_url(environment: str) -> str:
    return PRODUCTION_BASE if environment == "production" else SANDBOX_BASE


def validate_key_environment(api_key: str, environment: str) -> dict | None:
    """Local sanity check before any network call -- catches the most
    common connect_middesk mistake (pasting a live key while sandbox is
    selected, or vice versa). Returns a fail() dict, or None if fine."""
    key = (api_key or "").strip()
    if environment == "production" and key.startswith("mk_test_"):
        return fail(ENV_KEY_MISMATCH, "key looks like a sandbox key (mk_test_) but environment is production")
    if environment == "sandbox" and key.startswith("mk_live_"):
        return fail(ENV_KEY_MISMATCH, "key looks like a production key (mk_live_) but environment is sandbox")
    return None


def _headers(api_key: str, extra: dict | None = None) -> dict:
    h = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    if extra:
        h.update(extra)
    return h


def _check_status(resp, action: str) -> Any:
    if resp.status_code in (200, 201, 202):
        return resp.body if isinstance(resp.body, (dict, list)) else {}
    if resp.status_code == 204:
        return {}
    body = resp.body if isinstance(resp.body, dict) else {}
    detail = body.get("message") or body.get("error") or ""
    if resp.status_code == 401:
        raise ClientFail(fail(UNAUTHORIZED, f"{action}: {detail}" if detail else action))
    if resp.status_code == 403:
        raise ClientFail(fail(FORBIDDEN, f"{action}: {detail}" if detail else action))
    if resp.status_code == 404:
        raise ClientFail(fail(NOT_FOUND, f"{action}: {detail}" if detail else action))
    if resp.status_code == 429:
        raise ClientFail(fail(RATE_LIMITED, action))
    if resp.status_code >= 500:
        raise ClientFail(fail(BACKEND_5XX, action))
    if resp.status_code in (400, 422):
        raise ClientFail(fail(VALIDATION_FAILED, f"{action}: {detail}" if detail else action))
    raise ClientFail(fail(RESPONSE_UNEXPECTED, f"{action}: HTTP {resp.status_code} {detail}"))


async def check_connection(ctx, conn: dict) -> dict:
    """Live connectivity check: GET /businesses with a small page size.
    Returns {"ok": True} or a fail() dict. Used by connect_middesk and
    health_check, same shape as every other BYOK connector."""
    mismatch = validate_key_environment(conn.get("api_key", ""), conn.get("environment", "sandbox"))
    if mismatch:
        return mismatch
    url = f"{base_url(conn.get('environment', 'sandbox'))}/businesses"
    resp = await ctx.http.get(url, headers=_headers(conn.get("api_key", "")), params={"limit": 1})
    if resp.status_code == 401:
        return fail(UNAUTHORIZED)
    if resp.status_code == 403:
        return fail(FORBIDDEN)
    if resp.status_code >= 500:
        return fail(BACKEND_5XX)
    if resp.status_code != 200:
        return fail(RESPONSE_UNEXPECTED, f"HTTP {resp.status_code}")
    return {"ok": True}


async def request(
    ctx, conn: dict, method: str, path: str, *,
    json_body: dict | None = None, params: dict | None = None, action: str = "",
) -> Any:
    """Generic authenticated REST call against the Middesk API. `path` is
    relative to /v1, e.g. '/businesses' or '/businesses/{id}/orders'."""
    url = f"{base_url(conn.get('environment', 'sandbox'))}{path}"
    headers = _headers(conn.get("api_key", ""), {"Content-Type": "application/json"})
    if method == "GET":
        resp = await ctx.http.get(url, headers=headers, params=params)
    elif method == "POST":
        resp = await ctx.http.post(url, headers=headers, json=json_body or {})
    elif method == "PUT":
        resp = await ctx.http.put(url, headers=headers, json=json_body or {})
    elif method == "PATCH":
        resp = await ctx.http.patch(url, headers=headers, json=json_body or {})
    elif method == "DELETE":
        resp = await ctx.http.delete(url, headers=headers)
    else:
        raise ClientFail(fail(RESPONSE_UNEXPECTED, f"unsupported method {method}"))
    return _check_status(resp, action or f"{method} {path}")
