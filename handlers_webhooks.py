"""Webhook subscription management -- Middesk POSTs verification lifecycle
events to a registered URL, HMAC-signed. The connector manages the
subscription only; it does not host a receiver (same split as
Stripe/GitLab CI/CD/CircleCI Connector's webhook handlers elsewhere in
this portfolio).
"""
from __future__ import annotations

import json

from imperal_sdk import ActionResult

import middesk_client as mc
from handlers_connection import resolve_connection
from schemas import (
    CreateWebhookParams, GetWebhookParams, UpdateWebhookParams,
    DeleteWebhookParams, WebhookEntity, WebhookList, ListWebhooksParams,
    DeleteResult,
)
from app import chat


async def _conn_or_error(ctx, connection_id: str):
    conn = await resolve_connection(ctx, connection_id)
    if not conn:
        return None, ActionResult.error("No Middesk connection is saved. Call connect_middesk first.")
    return conn, None


def _webhook_from_body(body: dict) -> WebhookEntity:
    return WebhookEntity(
        id=body.get("id", ""), url=body.get("url", ""),
        event_types=body.get("event_types") or [],
        created_at=body.get("created_at", ""),
    )


@chat.function(
    name="create_webhook",
    description="Register a new webhook endpoint so Middesk pushes verification lifecycle events (business updates, review completion, monitor hits) to your URL as they happen.",
)
async def create_webhook(ctx, params: CreateWebhookParams) -> ActionResult[WebhookEntity]:
    """Register a new webhook endpoint so Middesk pushes verification lifecycle events (business updates, review completion, monitor hits) to your URL as they happen."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    payload: dict = {"url": params.url.strip()}
    if params.event_types_json.strip():
        try:
            payload["event_types"] = json.loads(params.event_types_json)
        except (TypeError, ValueError):
            return ActionResult.error("event_types_json must be valid JSON, e.g. '[\"business.updated\"]'.")
    try:
        body = await mc.request(ctx, conn, "POST", "/webhooks", json_body=payload, action="create_webhook")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    return ActionResult.success(_webhook_from_body(body), summary="Webhook registered.")


@chat.function(
    name="get_webhook",
    description="Read one webhook subscription's full configuration by id.",
)
async def get_webhook(ctx, params: GetWebhookParams) -> ActionResult[WebhookEntity]:
    """Read one webhook subscription's full configuration by id."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", f"/webhooks/{params.webhook_id}", action="get_webhook")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    return ActionResult.success(_webhook_from_body(body), summary=f"Webhook '{params.webhook_id}'.")


@chat.function(
    name="list_webhooks",
    description="List webhook subscriptions configured on the connected Middesk account.",
)
async def list_webhooks(ctx, params: ListWebhooksParams) -> ActionResult[WebhookList]:
    """List webhook subscriptions configured on the connected Middesk account."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", "/webhooks", action="list_webhooks")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    items = body.get("data", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    webhooks = [_webhook_from_body(w) for w in items]
    return ActionResult.success(WebhookList(webhooks=webhooks), summary=f"{len(webhooks)} webhook(s).")


@chat.function(
    name="update_webhook",
    description="Change an existing webhook's URL and/or subscribed event types. Only given fields change.",
)
async def update_webhook(ctx, params: UpdateWebhookParams) -> ActionResult[WebhookEntity]:
    """Change an existing webhook's URL and/or subscribed event types. Only given fields change."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    payload: dict = {}
    if params.url.strip():
        payload["url"] = params.url.strip()
    if params.event_types_json.strip():
        try:
            payload["event_types"] = json.loads(params.event_types_json)
        except (TypeError, ValueError):
            return ActionResult.error("event_types_json must be valid JSON.")
    if not payload:
        return ActionResult.error("Provide at least one field to update.")
    try:
        body = await mc.request(ctx, conn, "PATCH", f"/webhooks/{params.webhook_id}", json_body=payload, action="update_webhook")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    return ActionResult.success(_webhook_from_body(body), summary="Webhook updated.")


@chat.function(
    name="delete_webhook",
    description="Permanently remove a webhook subscription. Cannot be undone.",
    action_type="destructive",
    event="middesk-connector.delete_webhook",
    effects=["delete:resource"],
)
async def delete_webhook(ctx, params: DeleteWebhookParams) -> ActionResult[DeleteResult]:
    """Permanently remove a webhook subscription. Cannot be undone."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await mc.request(ctx, conn, "DELETE", f"/webhooks/{params.webhook_id}", action="delete_webhook")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    return ActionResult.success(DeleteResult(id=params.webhook_id), summary="Webhook removed.", refresh_panels=["sidebar"])
