"""Business Batches (bulk submission), Signals (raw risk data points),
Policy Results (automated ruleset decisions), and Actions (manual
re-verification triggers).
"""
from __future__ import annotations

import json

from imperal_sdk import ActionResult

import middesk_client as mc
from handlers_connection import resolve_connection
from schemas import (
    CreateBusinessBatchParams, GetBusinessBatchParams, BatchEntity,
    ListSignalsParams, SignalEntity, SignalList,
    ActionTriggerResult,
    ListPolicyResultsParams, PolicyResultEntity, PolicyResultList,
    CreateActionParams,
)
from app import chat


async def _conn_or_error(ctx, connection_id: str):
    conn = await resolve_connection(ctx, connection_id)
    if not conn:
        return None, ActionResult.error("No Middesk connection is saved. Call connect_middesk first.")
    return conn, None


@chat.function(
    name="create_business_batch",
    description="Submit several businesses to Middesk in one call (e.g. bulk-onboarding a portfolio of vendors), optionally kicking off the same verification products for every one of them.",
)
async def create_business_batch(ctx, params: CreateBusinessBatchParams) -> ActionResult[BatchEntity]:
    """Submit several businesses to Middesk in one call (e.g. bulk-onboarding a portfolio of vendors), optionally kicking off the same verification products for every one of them."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        businesses = json.loads(params.businesses_json)
    except (TypeError, ValueError):
        return ActionResult.error("businesses_json must be valid JSON.")
    if not isinstance(businesses, list) or not businesses:
        return ActionResult.error("businesses_json must decode to a non-empty JSON array of business objects.")
    payload: dict = {"businesses": businesses}
    if params.order_types_json.strip():
        try:
            payload["order_types"] = json.loads(params.order_types_json)
        except (TypeError, ValueError):
            return ActionResult.error("order_types_json must be valid JSON.")
    try:
        body = await mc.request(ctx, conn, "POST", "/business_batches", json_body=payload, action="create_business_batch")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    batch = BatchEntity(
        id=body.get("id", ""), status=body.get("status", ""),
        business_ids=body.get("business_ids") or [], created_at=body.get("created_at", ""),
    )
    return ActionResult.success(batch, summary=f"Business batch submitted with {len(businesses)} business(es).")


@chat.function(
    name="get_business_batch",
    description="Read one Business Batch's status -- which businesses it contains and whether processing is complete.",
)
async def get_business_batch(ctx, params: GetBusinessBatchParams) -> ActionResult[BatchEntity]:
    """Read one Business Batch's status -- which businesses it contains and whether processing is complete."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", f"/business_batches/{params.batch_id}", action="get_business_batch")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    batch = BatchEntity(
        id=body.get("id", ""), status=body.get("status", ""),
        business_ids=body.get("business_ids") or [], created_at=body.get("created_at", ""),
    )
    return ActionResult.success(batch, summary=f"Business batch '{batch.id}' -- {batch.status}.")


@chat.function(
    name="list_signals",
    description="List the raw risk signals Middesk has collected for a Business -- category, signal type, severity, and description behind each flag.",
)
async def list_signals(ctx, params: ListSignalsParams) -> ActionResult[SignalList]:
    """List the raw risk signals Middesk has collected for a Business -- category, signal type, severity, and description behind each flag."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", f"/businesses/{params.business_id}/signals", action="list_signals")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    items = body.get("data", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    signals = [
        SignalEntity(id=s.get("id", ""), category=s.get("category", ""), signal_type=s.get("signal_type", ""),
                     severity=s.get("severity", ""), description=s.get("description", ""))
        for s in items
    ]
    return ActionResult.success(SignalList(signals=signals), summary=f"{len(signals)} signal(s).")


@chat.function(
    name="list_policy_results",
    description="List automated ruleset/Policy decisions Middesk computed for a Business -- which policy fired and its outcome.",
)
async def list_policy_results(ctx, params: ListPolicyResultsParams) -> ActionResult[PolicyResultList]:
    """List automated ruleset/Policy decisions Middesk computed for a Business -- which policy fired and its outcome."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", f"/businesses/{params.business_id}/policy_results", action="list_policy_results")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    items = body.get("data", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    results = [
        PolicyResultEntity(id=p.get("id", ""), policy_name=p.get("policy_name", ""),
                            outcome=p.get("outcome", ""), created_at=p.get("created_at", ""))
        for p in items
    ]
    return ActionResult.success(PolicyResultList(results=results), summary=f"{len(results)} policy result(s).")


@chat.function(
    name="create_action",
    description="Manually trigger a Middesk action against a Business (e.g. force a re-verification) instead of waiting for scheduled monitoring.",
)
async def create_action(ctx, params: CreateActionParams) -> ActionResult[ActionTriggerResult]:
    """Trigger a manual verification action (e.g. reverify) against a Business."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    payload = {"action_type": params.action_type.strip()}
    try:
        body = await mc.request(ctx, conn, "POST", f"/businesses/{params.business_id}/actions", json_body=payload, action="create_action")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    return ActionResult.success(
        ActionTriggerResult(business_id=params.business_id, action_type=params.action_type, status=(body or {}).get("status", "triggered") if isinstance(body, dict) else "triggered"),
        summary=f"Action '{params.action_type}' triggered.",
    )
