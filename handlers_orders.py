"""Orders -- request specific verification products (identity, tin,
watchlist, industry_classification, web_presence, risk, etc.) against an
already-created Business. Same connection-resolution pattern as
handlers_business.py.
"""
from __future__ import annotations

import json

from imperal_sdk import ActionResult

import middesk_client as mc
from handlers_connection import resolve_connection
from schemas import (
    CreateOrderParams, GetOrderParams, ListOrdersParams,
    OrderEntity, OrderList,
)
from app import chat


async def _conn_or_error(ctx, connection_id: str):
    conn = await resolve_connection(ctx, connection_id)
    if not conn:
        return None, ActionResult.error("No Middesk connection is saved. Call connect_middesk first.")
    return conn, None


def _order_from_body(body: dict) -> OrderEntity:
    return OrderEntity(
        id=body.get("id", ""),
        business_id=body.get("business_id", ""),
        status=body.get("status", ""),
        order_types=body.get("order_types") or [],
        created_at=body.get("created_at", ""),
        updated_at=body.get("updated_at", ""),
    )


@chat.function(
    name="create_order",
    description="Order one or more verification products (e.g. identity, tin, watchlist, industry_classification, web_presence, risk) against an existing Business.",
)
async def create_order(ctx, params: CreateOrderParams) -> ActionResult[OrderEntity]:
    """Order one or more verification products (e.g. identity, tin, watchlist, industry_classification, web_presence, risk) against an existing Business."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        order_types = json.loads(params.order_types_json)
    except (TypeError, ValueError):
        return ActionResult.error("order_types_json must be valid JSON, e.g. '[\"identity\",\"tin\"]'.")
    if not isinstance(order_types, list) or not order_types:
        return ActionResult.error("order_types_json must decode to a non-empty JSON array of product names.")
    payload = {"order_types": order_types}
    try:
        body = await mc.request(ctx, conn, "POST", f"/businesses/{params.business_id}/orders", json_body=payload, action="create_order")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    return ActionResult.success(_order_from_body(body), summary=f"Order created for {len(order_types)} product(s).", refresh_panels=["sidebar"])


@chat.function(
    name="get_order",
    description="Read one verification Order in full -- its status and which products were requested.",
)
async def get_order(ctx, params: GetOrderParams) -> ActionResult[OrderEntity]:
    """Read one verification Order in full -- its status and which products were requested."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", f"/businesses/{params.business_id}/orders/{params.order_id}", action="get_order")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    return ActionResult.success(_order_from_body(body), summary=f"Order '{params.order_id}' is {body.get('status', 'unknown')}.")


@chat.function(
    name="list_orders",
    description="List every verification Order placed against one Business.",
)
async def list_orders(ctx, params: ListOrdersParams) -> ActionResult[OrderList]:
    """List every verification Order placed against one Business."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", f"/businesses/{params.business_id}/orders", action="list_orders")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    items = body.get("data", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    return ActionResult.success(OrderList(orders=[_order_from_body(o) for o in items]), summary=f"{len(items)} order(s).")
