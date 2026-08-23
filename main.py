"""Entrypoint for the web-kernel and CLI tools (imperal validate/build).

Sets up sys.path, purges stale module cache, then imports ext/chat and all
handler modules so their decorators register on the same Extension
instance -- same pattern as DocuSign Connector's / CircleCI Connector's
main.py.
"""

import os
import sys

_EXT_DIR = os.path.dirname(os.path.abspath(__file__))
if _EXT_DIR not in sys.path:
    sys.path.insert(0, _EXT_DIR)

_LOCAL = (
    "app", "schemas", "middesk_client",
    "handlers_connection", "handlers_business", "handlers_orders",
    "handlers_review", "handlers_monitor", "handlers_risk_data",
    "handlers_batch", "handlers_webhooks", "handlers_entity",
    "handlers_agents", "handlers_prefill", "handlers_audit",
    "panels", "panels_settings",
)
for _mod in _LOCAL:
    sys.modules.pop(_mod, None)

from app import ext, chat  # noqa: E402,F401
import handlers_connection  # noqa: E402,F401
import handlers_business  # noqa: E402,F401
import handlers_orders  # noqa: E402,F401
import handlers_review  # noqa: E402,F401
import handlers_monitor  # noqa: E402,F401
import handlers_risk_data  # noqa: E402,F401
import handlers_batch  # noqa: E402,F401
import handlers_webhooks  # noqa: E402,F401
import handlers_entity  # noqa: E402,F401
import handlers_agents  # noqa: E402,F401
import handlers_prefill  # noqa: E402,F401
import handlers_audit  # noqa: E402,F401
import panels  # noqa: E402,F401
import panels_settings  # noqa: E402,F401
