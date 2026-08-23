"""Monitoring -- ongoing continuous re-verification of an already-approved
Business (SOS deactivation, new watchlist hits, officer changes, etc.).
Egress/Both value-add functionality, same audit-style pattern as
PagerDuty/DocuSign 'audit' handlers elsewhere in the portfolio.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import middesk_client as mc
from handlers_connection import resolve_connection
from schemas import (
    CreateMonitorParams, GetMonitorParams, DeleteMonitorParams,
    MonitorEntity, ListMonitorEventsParams, MonitorEvent, MonitorEventList,
    DeleteResult,
)
from app import chat


async def _conn_or_error(ctx, connection_id: str):
    conn = await resolve_connection(ctx, connection_id)
    if not conn:
        return None, ActionResult.error("No Middesk connection is saved. Call connect_middesk first.")
    return conn, None


def _monitor_from_body(body: dict) -> MonitorEntity:
    return MonitorEntity(
        id=body.get("id", ""), business_id=body.get("business_id", ""),
        status=body.get("status", "active"), created_at=body.get("created_at", ""),
    )


@chat.function(
    name="create_monitor",
    description="Subscribe a Business to ongoing monitoring -- Middesk continuously re-checks it for SOS deactivation, new watchlist/sanctions hits, and officer/registration changes after initial approval.",
    action_type="write",
    effects=["create:monitor"],
    event="middesk-connector.create_monitor",
)
async def create_monitor(ctx, params: CreateMonitorParams) -> ActionResult[MonitorEntity]:
    """Subscribe a Business to ongoing monitoring -- Middesk continuously re-checks it for SOS deactivation, new watchlist/sanctions hits, and officer/registration changes after initial approval."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "POST", f"/businesses/{params.business_id}/monitor", action="create_monitor")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    return ActionResult.success(_monitor_from_body(body), summary="Monitoring started.", refresh_panels=["sidebar"])


@chat.function(
    name="get_monitor",
    description="Read a Business's Monitor status -- whether ongoing monitoring is currently active.",
)
async def get_monitor(ctx, params: GetMonitorParams) -> ActionResult[MonitorEntity]:
    """Read a Business's Monitor status -- whether ongoing monitoring is currently active."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", f"/businesses/{params.business_id}/monitor", action="get_monitor")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    return ActionResult.success(_monitor_from_body(body), summary=f"Monitor is {body.get('status', 'unknown')}.")


@chat.function(
    name="delete_monitor",
    description="Stop ongoing monitoring for a Business. Cannot be undone -- create_monitor again to resume.",
    action_type="destructive",
    event="middesk-connector.delete_monitor",
    effects=["delete:resource"],
)
async def delete_monitor(ctx, params: DeleteMonitorParams) -> ActionResult[DeleteResult]:
    """Stop ongoing monitoring for a Business. Cannot be undone."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await mc.request(ctx, conn, "DELETE", f"/businesses/{params.business_id}/monitor", action="delete_monitor")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    return ActionResult.success(DeleteResult(id=params.business_id, deleted=True), summary="Monitoring stopped.", refresh_panels=["sidebar"])


@chat.function(
    name="list_monitor_events",
    description="List events raised by ongoing monitoring for a Business -- e.g. a new watchlist hit or a Secretary of State status change detected after approval.",
)
async def list_monitor_events(ctx, params: ListMonitorEventsParams) -> ActionResult[MonitorEventList]:
    """List events raised by ongoing monitoring for a Business -- e.g. a new watchlist hit or a Secretary of State status change detected after approval."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", f"/businesses/{params.business_id}/monitor/events", action="list_monitor_events")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    items = body.get("data", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    events = [MonitorEvent(id=e.get("id", ""), event_type=e.get("event_type", ""), created_at=e.get("created_at", ""), summary=e.get("summary", "")) for e in items]
    return ActionResult.success(MonitorEventList(events=events), summary=f"{len(events)} monitor event(s).")
