"""Connection management for Middesk Connector: connect/disconnect/list.
Static API key auth (no OAuth), connections stored as a JSON array under
one secret, same shape as DocuSign/CircleCI/GitLab CI/CD/ShipStation/
Ironclad Connector's handlers_connection.py.
"""
from __future__ import annotations

import json
import uuid

from imperal_sdk import ActionResult

import middesk_client as mc
from app import ext, chat
from schemas import (
    NoParams,
    ConnectMiddeskParams, MiddeskConnection, MiddeskConnectionList,
    DisconnectMiddeskParams, DeleteResult,
)

_SECRET_NAME = "middesk_connections"


async def _load_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_SECRET_NAME)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


async def _save_connections(ctx, connections: list[dict]) -> None:
    await ctx.secrets.set(_SECRET_NAME, json.dumps(connections))


async def resolve_connection(ctx, connection_id: str = "") -> dict | None:
    connections = await _load_connections(ctx)
    if not connections:
        return None
    if connection_id:
        for c in connections:
            if c.get("id") == connection_id:
                return c
        return None
    return connections[0]


def _mask(api_key: str) -> str:
    key = api_key or ""
    if len(key) <= 8:
        return "***"
    return f"{key[:7]}...{key[-4:]}"


def _connection_to_entity(c: dict) -> MiddeskConnection:
    return MiddeskConnection(
        id=c.get("id", ""),
        label=c.get("label") or c.get("environment", ""),
        environment=c.get("environment", "sandbox"),
        masked_api_key=_mask(c.get("api_key", "")),
        connected_at=c.get("connected_at", ""),
        status=c.get("status", "connected"),
    )


@chat.function(
    name="connect_middesk",
    description=(
        "Connect your own Middesk account by saving an API key for a chosen "
        "environment (sandbox or production), after checking it actually works."
    ),
)
async def connect_middesk(ctx, params: ConnectMiddeskParams) -> ActionResult[MiddeskConnection]:
    """Save a Middesk API key + environment after a live connectivity check."""
    environment = params.environment if params.environment in ("sandbox", "production") else "sandbox"
    conn = {
        "api_key": params.api_key.strip(),
        "environment": environment,
        "label": params.label.strip(),
    }
    check = await mc.check_connection(ctx, conn)
    if not check.get("ok"):
        return ActionResult.error(check.get("error", "Could not verify this Middesk API key."), retryable=check.get("retryable", False))

    connections = await _load_connections(ctx)
    new_id = str(uuid.uuid4())
    record = {
        "id": new_id,
        "api_key": conn["api_key"],
        "environment": environment,
        "label": params.label.strip(),
        "connected_at": "",
        "status": "connected",
    }
    connections.append(record)
    await _save_connections(ctx, connections)
    return ActionResult.success(
        _connection_to_entity(record),
        summary=f"Connected Middesk ({environment}).",
        refresh_panels=["sidebar"],
    )


@chat.function(
    name="disconnect_middesk",
    description="Disconnect a Middesk account: deletes the saved API key. Nothing in Middesk itself is changed.",
)
async def disconnect_middesk(ctx, params: DisconnectMiddeskParams) -> ActionResult[DeleteResult]:
    """Disconnect a Middesk account: deletes the saved API key. Nothing in Middesk itself is changed."""
    connections = await _load_connections(ctx)
    if not connections:
        return ActionResult.error("No Middesk connection is saved.")
    target_id = params.connection_id or connections[0].get("id", "")
    remaining = [c for c in connections if c.get("id") != target_id]
    if len(remaining) == len(connections):
        return ActionResult.error(f"No connection found with id '{target_id}'.")
    await _save_connections(ctx, remaining)
    return ActionResult.success(
        DeleteResult(id=target_id, deleted=True),
        summary="Disconnected Middesk.",
        refresh_panels=["sidebar"],
    )


@chat.function(
    name="list_connections",
    description="List the connected Middesk accounts and whether each saved API key still works.",
)
async def list_connections(ctx, params: NoParams) -> ActionResult[MiddeskConnectionList]:
    """List the connected Middesk accounts and whether each saved API key still works."""
    connections = await _load_connections(ctx)
    return ActionResult.success(
        MiddeskConnectionList(connections=[_connection_to_entity(c) for c in connections]),
        summary=f"{len(connections)} Middesk connection(s).",
    )
