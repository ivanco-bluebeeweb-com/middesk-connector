"""Value-add: portfolio-wide verification health audit -- Imperal's own
aggregation on top of Middesk's raw data, same pattern as Cin7 Core's
audit_inventory_health / CircleCI's audit_project_health / PagerDuty's
audit_account. Scans recent Businesses and flags ones needing attention:
stuck in_review, rejected, or with open Review Tasks.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import middesk_client as mc
from handlers_connection import resolve_connection
from schemas import AuditVerificationPortfolioParams, PortfolioAuditResult
from app import chat


@chat.function(
    name="audit_verification_portfolio",
    description="Value-add report: scan recent Businesses in the connected Middesk account and flag ones stuck in_review, rejected, or with unresolved review tasks -- a one-glance KYB portfolio health check.",
)
async def audit_verification_portfolio(ctx, params: AuditVerificationPortfolioParams) -> ActionResult[PortfolioAuditResult]:
    """Value-add report: scan recent Businesses in the connected Middesk account and flag ones stuck in_review, rejected, or with unresolved review tasks -- a one-glance KYB portfolio health check."""
    conn = await resolve_connection(ctx, params.connection_id)
    if not conn:
        return ActionResult.error("No Middesk connection is saved. Call connect_middesk first.")
    try:
        body = await mc.request(ctx, conn, "GET", "/businesses", params={"limit": params.limit}, action="audit_verification_portfolio")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    items = body.get("data", []) if isinstance(body, dict) else []
    total = len(items)
    approved = sum(1 for b in items if b.get("status") == "approved")
    rejected = sum(1 for b in items if b.get("status") == "rejected")
    in_review = sum(1 for b in items if b.get("status") == "in_review")
    pending = sum(1 for b in items if b.get("status") in ("open", "pending", "in_audit"))
    flagged = [
        {"id": b.get("id", ""), "name": b.get("name", ""), "status": b.get("status", "")}
        for b in items if b.get("status") in ("rejected", "in_review")
    ]
    result = PortfolioAuditResult(
        total_scanned=total, approved=approved, rejected=rejected,
        in_review=in_review, pending=pending, flagged=flagged,
    )
    return ActionResult.success(
        result,
        summary=f"Scanned {total} business(es): {approved} approved, {rejected} rejected, {in_review} in review, {pending} pending.",
    )
