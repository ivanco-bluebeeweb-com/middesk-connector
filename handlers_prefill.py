"""Prefill/Risk -- fast onboarding-time helpers: autocomplete identities
(business-name-as-you-type suggestions), smart populate (fill a form from
partial input), and standalone risk assessments (no full Business Order
needed). See docs.middesk.com prefill/risk sections.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import middesk_client as mc
from handlers_connection import resolve_connection
from schemas import (
    AutocompleteIdentityParams, IdentitySuggestion, IdentitySuggestionList,
    SmartPopulateParams, SmartPopulateResult,
    RunRiskAssessmentParams, RiskAssessmentResult,
)
from app import chat


async def _conn_or_error(ctx, connection_id: str):
    conn = await resolve_connection(ctx, connection_id)
    if not conn:
        return None, ActionResult.error("No Middesk connection is saved. Call connect_middesk first.")
    return conn, None


@chat.function(
    name="autocomplete_identity",
    description="Get business-identity autocomplete suggestions for a partial name/address -- for a fast, low-friction onboarding form before a full KYB order.",
)
async def autocomplete_identity(ctx, params: AutocompleteIdentityParams) -> ActionResult[IdentitySuggestionList]:
    """Get business-identity autocomplete suggestions for a partial name/address -- for a fast, low-friction onboarding form before a full KYB order."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    query = {"query": params.query.strip()}
    try:
        body = await mc.request(ctx, conn, "GET", "/prefill/autocomplete", params=query, action="autocomplete_identity")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    items = body.get("data", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    suggestions = [
        IdentitySuggestion(name=s.get("name", ""), address=s.get("address", ""), tin=s.get("tin"))
        for s in items
    ]
    return ActionResult.success(IdentitySuggestionList(suggestions=suggestions), summary=f"{len(suggestions)} suggestion(s).")


@chat.function(
    name="smart_populate",
    description="Auto-fill a full business profile from a partial input (e.g. just a name), so an onboarding form can be pre-filled before the user finishes typing.",
    action_type="write",
    effects=["create:prefill_result"],
    event="middesk-connector.smart_populate",
)
async def smart_populate(ctx, params: SmartPopulateParams) -> ActionResult[SmartPopulateResult]:
    """Auto-fill a full business profile from a partial input (e.g. just a name), so an onboarding form can be pre-filled before the user finishes typing."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    payload = {"name": params.name.strip()}
    if params.state.strip():
        payload["state"] = params.state.strip()
    try:
        body = await mc.request(ctx, conn, "POST", "/prefill/smart-populate", json_body=payload, action="smart_populate")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    result = SmartPopulateResult(
        name=body.get("name", ""), address=body.get("address", ""),
        tin=body.get("tin"), website=body.get("website"),
        confidence=body.get("confidence", ""),
    )
    return ActionResult.success(result, summary="Smart-populate result ready.")


@chat.function(
    name="run_risk_assessment",
    description="Run a standalone, fast risk assessment on a business identity without opening a full Business Order -- useful for a quick pre-screen before deciding whether to run the full KYB flow.",
    action_type="write",
    effects=["create:risk_assessment"],
    event="middesk-connector.run_risk_assessment",
)
async def run_risk_assessment(ctx, params: RunRiskAssessmentParams) -> ActionResult[RiskAssessmentResult]:
    """Run a standalone, fast risk assessment on a business identity without opening a full Business Order -- useful for a quick pre-screen before deciding whether to run the full KYB flow."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    payload: dict = {"name": params.name.strip()}
    if params.tin.strip():
        payload["tin"] = params.tin.strip()
    if params.website.strip():
        payload["website"] = params.website.strip()
    try:
        body = await mc.request(ctx, conn, "POST", "/prefill/risk-assessment", json_body=payload, action="run_risk_assessment")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    result = RiskAssessmentResult(
        risk_level=body.get("risk_level", ""), score=body.get("score"),
        reasons=body.get("reasons") or [],
    )
    return ActionResult.success(result, summary=f"Risk level: {result.risk_level or 'unknown'}.")
