"""Extension declaration, secrets, lifecycle hooks.

WHY BYOK (bring-your-own-key), same reasoning as Cin7 Core Connector /
CircleCI Connector / ShipStation Connector / PagerDuty Connector. A
Middesk account lives inside the USER'S OWN Middesk account -- Imperal
cannot and should not broker access to someone else's KYB/compliance data
centrally.

WHY STATIC API KEY, NOT OAUTH.

Middesk has no OAuth flow for API clients at all (confirmed
docs.middesk.com/build/api-keys, 2026-08-22/23) -- just a static API key
per environment (sandbox `mk_test_...` / production `mk_live_...`), used
as a Bearer token. So there is no ext.oauth provider here and no consent
URL step -- connect_middesk saves the key + environment pair directly
after a live connectivity check (GET /v1/businesses), same shape as
Cin7 Core's Account ID + Application Key.

WHY TWO ENVIRONMENTS (sandbox/production) AS A REQUIRED FIELD, NOT A
QUERY FLAG, SAME REASONING AS DOCUSIGN'S demo/production.

Middesk's sandbox (`api-sandbox.middesk.com`) and production
(`api.middesk.com`) are physically separate base URLs with separate key
prefixes (`mk_test_...` / `mk_live_...`) -- the key type and URL must
match or Middesk rejects the request. The user picks one at connect time
(default sandbox, for a safe first test), stored per connection.

WHY SCOPE IS PER-ACCOUNT, NOT APP-LEVEL, SAME AS EVERY OTHER BYOK
CONNECTOR IN THIS PORTFOLIO.

A user may hold a sandbox connection and a production connection side by
side (to validate policies before going live) -- connections are stored
as a JSON array under one secret, each entry with its own API key/
environment, identical shape to DocuSign/CircleCI/GitLab CI/CD/
ShipStation/Ironclad Connector's `*_connections` list.

WHY DESTRUCTIVE ACTIONS ARE MARKED `action_type="destructive"`, SAME
PRINCIPLE AS EVERY OTHER CONNECTOR IN THIS PORTFOLIO.

Deleting a monitor, webhook, or disconnecting an account cannot be undone
through this connector -- each such handler declares
`action_type="destructive"` so the platform's own confirmation card gates
the call.
"""
from __future__ import annotations

from imperal_sdk import ChatExtension, Extension

ext = Extension(
    "middesk-connector",
    version="0.1.0",
    display_name="Middesk",
    description=(
        "Connect your own Middesk account to run KYB (Know Your Business) "
        "verification end to end: create Businesses and Orders (identity, "
        "TIN, watchlist/sanctions, industry classification, web presence, "
        "risk), read Review/Review Tasks, timeline, signals, liens, "
        "Secretary of State registrations, TIN match, websites, and "
        "documents, set up ongoing Monitors and Monitor Events, register "
        "webhooks, run Entity Management payroll-tax registrations, and "
        "drive Middesk's AI verification Agents. Uses your own Middesk "
        "API key -- nothing is hosted or proxied by Imperal beyond the "
        "request itself."
    ),
    icon="icon.svg",
    capabilities=[
        "middesk:read",
        "middesk:write",
    ],
    actions_explicit=True,
    system=False,
)

chat = ChatExtension(
    ext,
    tool_name="middesk",
    description=(
        "Middesk Connector -- connect your own Middesk account via a "
        "static API key (sandbox or production), then create/verify "
        "Businesses, run Orders for KYB products, read Review results, "
        "liens/registrations/TIN/websites, set up ongoing Monitors, "
        "manage webhooks, register entities for payroll taxes, and drive "
        "AI verification Agents."
    ),
)

ext.secret(
    "middesk_connections",
    (
        "Your connected Middesk accounts -- stored as a JSON array, one "
        "entry per account, each with its API key, environment (sandbox/"
        "production), and an optional label. Managed through "
        "connect_middesk / disconnect_middesk -- you should not need to "
        "edit this directly."
    ),
    required=True,
    write_mode="both",
    max_bytes=65536,
    rotation_hint_days=180,
)(lambda: None)


@ext.health_check
async def health_check(ctx) -> dict:
    """Fast configuration health; no third-party call -- just confirms at
    least one connection is stored, same shape as CircleCI Connector's /
    DocuSign Connector's health_check."""
    import json as _json
    raw = await ctx.secrets.get("middesk_connections")
    try:
        count = len(_json.loads(raw)) if raw else 0
    except Exception:
        count = 0
    return {
        "healthy": True,
        "detail": (
            f"{count} Middesk account(s) connected." if count
            else "Not connected yet -- run connect_middesk."
        ),
    }
