"""Business Verification core: Business CRUD + timeline. Same async
ctx-based connection-resolution pattern as handlers_connection.py.
"""
from __future__ import annotations

import json

from imperal_sdk import ActionResult

import middesk_client as mc
from app import ext, chat
from handlers_connection import resolve_connection
from schemas import (
    CreateBusinessParams, UpdateBusinessParams, GetBusinessParams,
    ListBusinessesParams, BusinessEntity, BusinessList,
    ListBusinessTimelineParams, TimelineEvent, TimelineEventList,
)


async def _conn_or_error(ctx, connection_id: str):
    conn = await resolve_connection(ctx, connection_id)
    if not conn:
        return None, ActionResult.error("No Middesk connection is saved. Call connect_middesk first.")
    return conn, None


def _business_from_body(body: dict) -> BusinessEntity:
    return BusinessEntity(
        id=body.get("id", ""),
        name=body.get("name", ""),
        status=body.get("status", ""),
        created_at=body.get("created_at", ""),
        updated_at=body.get("updated_at", ""),
        external_id=body.get("external_id"),
        tin=(body.get("tin") or {}).get("tin") if isinstance(body.get("tin"), dict) else body.get("tin"),
        website=body.get("website"),
        tags=body.get("tags") or [],
        review_id=(body.get("review") or {}).get("id") if isinstance(body.get("review"), dict) else None,
    )


@chat.function(
    name="create_business",
    description="Create a new Business in Middesk to start KYB verification -- name plus optional TIN/address/website, and optionally kick off verification products (orders) immediately.",
)
async def create_business(ctx, params: CreateBusinessParams) -> ActionResult[BusinessEntity]:
    """Create a new Business in Middesk to start KYB verification -- name plus optional TIN/address/website, and optionally kick off verification products (orders) immediately."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    payload: dict = {"name": params.name.strip()}
    if params.tin.strip():
        payload["tin"] = params.tin.strip()
    if params.website.strip():
        payload["website"] = params.website.strip()
    if params.external_id.strip():
        payload["external_id"] = params.external_id.strip()
    if params.addresses_json.strip():
        try:
            payload["addresses"] = json.loads(params.addresses_json)
        except (TypeError, ValueError):
            return ActionResult.error("addresses_json is not valid JSON.")
    if params.order_types_json.strip():
        try:
            payload["order"] = {"order_types": json.loads(params.order_types_json)}
        except (TypeError, ValueError):
            return ActionResult.error("order_types_json is not valid JSON.")
    try:
        body = await mc.request(ctx, conn, "POST", "/businesses", json_body=payload, action="create_business")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    return ActionResult.success(_business_from_body(body), summary=f"Created business '{params.name}'.", refresh_panels=["sidebar"])


@chat.function(
    name="update_business",
    description="Update selected fields of an existing Business (name/TIN/external_id/tags). Only given fields change.",
)
async def update_business(ctx, params: UpdateBusinessParams) -> ActionResult[BusinessEntity]:
    """Update selected fields of an existing Business (name/TIN/external_id/tags). Only given fields change."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    payload: dict = {}
    if params.name.strip():
        payload["name"] = params.name.strip()
    if params.tin.strip():
        payload["tin"] = params.tin.strip()
    if params.external_id.strip():
        payload["external_id"] = params.external_id.strip()
    if params.tags_json.strip():
        try:
            payload["tags"] = json.loads(params.tags_json)
        except (TypeError, ValueError):
            return ActionResult.error("tags_json is not valid JSON.")
    if not payload:
        return ActionResult.error("No fields given to update.")
    try:
        body = await mc.request(ctx, conn, "PUT", f"/businesses/{params.business_id}", json_body=payload, action="update_business")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    return ActionResult.success(_business_from_body(body), summary="Business updated.", refresh_panels=["sidebar"])


@chat.function(
    name="get_business",
    description="Read one Business in full: verification status, TIN, tags, and its review id.",
)
async def get_business(ctx, params: GetBusinessParams) -> ActionResult[BusinessEntity]:
    """Read one Business in full: verification status, TIN, tags, and its review id."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", f"/businesses/{params.business_id}", action="get_business")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    return ActionResult.success(_business_from_body(body), summary=f"Business '{body.get('name', '')}'.")


@chat.function(
    name="list_businesses",
    description="List Businesses in the connected Middesk account, optionally filtered by verification status.",
)
async def list_businesses(ctx, params: ListBusinessesParams) -> ActionResult[BusinessList]:
    """List Businesses in the connected Middesk account, optionally filtered by verification status."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    query: dict = {"limit": params.limit}
    if params.status.strip():
        query["status"] = params.status.strip()
    try:
        body = await mc.request(ctx, conn, "GET", "/businesses", params=query, action="list_businesses")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    items = body.get("data", []) if isinstance(body, dict) else []
    return ActionResult.success(
        BusinessList(businesses=[_business_from_body(b) for b in items], has_more=bool(body.get("has_more"))),
        summary=f"{len(items)} business(es).",
    )


@chat.function(
    name="list_business_timeline",
    description="Read the event timeline of one Business -- every status change and verification milestone in order.",
)
async def list_business_timeline(ctx, params: ListBusinessTimelineParams) -> ActionResult[TimelineEventList]:
    """Read the event timeline of one Business -- every status change and verification milestone in order."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", f"/businesses/{params.business_id}/timeline", action="list_business_timeline")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    items = body.get("data", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    events = [
        TimelineEvent(id=e.get("id", ""), type=e.get("type", ""), created_at=e.get("created_at", ""), data_summary=str(e.get("data", ""))[:200])
        for e in items
    ]
    return ActionResult.success(TimelineEventList(events=events), summary=f"{len(events)} timeline event(s).")
