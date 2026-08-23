# Pricing History — Middesk Connector

Mandatory ledger: every initial price or change for this app is recorded here — what changed, why, and the outcome. Keep prior entries; add new entries above them.

---

## 2026-08-23 — initial pricing, per_action, revenue_split_dev=95

**Price scale:** `{0, 8, 16, 20, 40, 60}` credits, assigned explicitly to all 48 actions in `tool-prices.json`.

| Price | Category | Middesk examples |
|---:|---|---|
| 0 | Connection setup/teardown | `connect_middesk`, `disconnect_middesk`, `list_connections` |
| 8 | Read, lookup, and list operations | `get_business`, `list_orders`, `get_review`, `list_signals`, `autocomplete_identity` |
| 16 | Standard configuration/record writes | `create_business`, `update_business`, webhook CRUD, registration requests, agent threads |
| 20 | Operational verification actions | ordering KYB products, monitoring, reverify actions, information-request answers, AI agent runs, risk/prefill assessment |
| 40 | Aggregated value-add report | `audit_verification_portfolio` |
| 60 | Bulk portfolio onboarding | `create_business_batch` |

**Verification:** The first `save_pricing` response reported a real storage mismatch (model remained `free` and action prices absent) despite no API failure. A second identical save succeeded. Independent marketplace query then confirmed `pricing_model=per_action`; explicit local map is committed as `tool-prices.json`.

**Release quality gate:** v1.0.0 has 48 tools, all external mutations correctly declared `action_type="write"` or `destructive`, with effects and events. `imperal validate .` completed with **0 errors and 0 warnings** (only optional V12 lifecycle-hook info remains).
