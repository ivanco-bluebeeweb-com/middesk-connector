"""Review, Review Tasks, and Review Insights -- the consolidated
verification result of a Business (see docs.middesk.com/review-insights).
Read-only: Middesk computes these, the connector only surfaces them.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import middesk_client as mc
from handlers_connection import resolve_connection
from schemas import (
    GetReviewParams, ReviewTask, ReviewEntity,
    ListReviewInsightsParams, ReviewInsight, ReviewInsightList,
)
from app import chat


async def _conn_or_error(ctx, connection_id: str):
    conn = await resolve_connection(ctx, connection_id)
    if not conn:
        return None, ActionResult.error("No Middesk connection is saved. Call connect_middesk first.")
    return conn, None


@chat.function(
    name="get_review",
    description="Read a Business's Review in full -- overall status plus every Review Task (category, key, and outcome) that fed into the verification decision.",
)
async def get_review(ctx, params: GetReviewParams) -> ActionResult[ReviewEntity]:
    """Read a Business's Review in full -- overall status plus every Review Task (category, key, and outcome) that fed into the verification decision."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", f"/businesses/{params.business_id}/review", action="get_review")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    tasks = [
        ReviewTask(
            category=t.get("category", ""), key=t.get("key", ""),
            label=t.get("label", ""), status=t.get("status", ""),
            reasons=t.get("reasons") or [],
        )
        for t in (body.get("tasks") or [])
    ]
    review = ReviewEntity(
        id=body.get("id", ""), status=body.get("status", ""),
        created_at=body.get("created_at", ""), updated_at=body.get("updated_at", ""),
        tasks=tasks,
    )
    return ActionResult.success(review, summary=f"Review has {len(tasks)} task(s).")


@chat.function(
    name="list_review_insights",
    description="Read consolidated, human-readable Review Insights for a Business -- Middesk's own summarized findings across every verification category.",
)
async def list_review_insights(ctx, params: ListReviewInsightsParams) -> ActionResult[ReviewInsightList]:
    """Read consolidated, human-readable Review Insights for a Business -- Middesk's own summarized findings across every verification category."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", f"/businesses/{params.business_id}/insights", action="list_review_insights")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    items = body.get("data", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    insights = [
        ReviewInsight(category=i.get("category", ""), summary=i.get("summary", ""), severity=i.get("severity", ""))
        for i in items
    ]
    return ActionResult.success(ReviewInsightList(insights=insights), summary=f"{len(insights)} insight(s).")
