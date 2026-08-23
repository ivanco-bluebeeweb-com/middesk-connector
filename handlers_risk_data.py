"""Risk/registration data reads -- Liens (UCC/tax), Secretary of State
Registrations, TIN match result, Documents, and Websites for a Business.
All read-only surfaces of data Middesk already collected via Orders.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import middesk_client as mc
from handlers_connection import resolve_connection
from schemas import (
    ListLiensParams, LienEntity, LienList,
    ListRegistrationsParams, RegistrationEntity, RegistrationList,
    GetTinParams, TinEntity,
    ListDocumentsParams, DocumentEntity, DocumentList,
    ListWebsitesParams, WebsiteEntity, WebsiteList,
)
from app import chat


async def _conn_or_error(ctx, connection_id: str):
    conn = await resolve_connection(ctx, connection_id)
    if not conn:
        return None, ActionResult.error("No Middesk connection is saved. Call connect_middesk first.")
    return conn, None


@chat.function(
    name="list_liens",
    description="List UCC and tax liens filed against a Business -- filing type, status, filing number/date, and jurisdiction.",
)
async def list_liens(ctx, params: ListLiensParams) -> ActionResult[LienList]:
    """List UCC and tax liens filed against a Business -- filing type, status, filing number/date, and jurisdiction."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", f"/businesses/{params.business_id}/liens", action="list_liens")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    items = body.get("data", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    liens = [
        LienEntity(id=l.get("id", ""), lien_type=l.get("lien_type", ""), status=l.get("status", ""),
                   filing_number=l.get("filing_number", ""), filing_date=l.get("filing_date", ""),
                   jurisdiction=l.get("jurisdiction", ""))
        for l in items
    ]
    return ActionResult.success(LienList(liens=liens), summary=f"{len(liens)} lien(s).")


@chat.function(
    name="list_registrations",
    description="List Secretary of State business registrations for a Business across every state it's registered in -- status, entity type, and standing.",
)
async def list_registrations(ctx, params: ListRegistrationsParams) -> ActionResult[RegistrationList]:
    """List Secretary of State business registrations for a Business across every state it's registered in -- status, entity type, and standing."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", f"/businesses/{params.business_id}/registrations", action="list_registrations")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    items = body.get("data", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    regs = [
        RegistrationEntity(id=r.get("id", ""), state=r.get("state", ""), status=r.get("status", ""),
                            entity_type=r.get("entity_type", ""), registration_date=r.get("registration_date", ""),
                            standing=r.get("standing", ""))
        for r in items
    ]
    return ActionResult.success(RegistrationList(registrations=regs), summary=f"{len(regs)} registration(s).")


@chat.function(
    name="get_tin",
    description="Read the TIN/EIN match result for a Business -- whether the tax ID matches IRS records, and the TIN type.",
)
async def get_tin(ctx, params: GetTinParams) -> ActionResult[TinEntity]:
    """Read the TIN/EIN match result for a Business -- whether the tax ID matches IRS records, and the TIN type."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", f"/businesses/{params.business_id}/tin", action="get_tin")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    tin = TinEntity(id=body.get("id", ""), tin=body.get("tin", ""), tin_type=body.get("tin_type", ""),
                     match_result=body.get("match_result", ""), matched_name=body.get("matched_name", ""))
    return ActionResult.success(tin, summary=f"TIN match result: {tin.match_result or 'unknown'}.")


@chat.function(
    name="list_documents",
    description="List documents Middesk has collected or generated for a Business (e.g. Secretary of State filings, formation documents).",
)
async def list_documents(ctx, params: ListDocumentsParams) -> ActionResult[DocumentList]:
    """List documents Middesk has collected or generated for a Business (e.g. Secretary of State filings, formation documents)."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", f"/businesses/{params.business_id}/documents", action="list_documents")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    items = body.get("data", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    docs = [
        DocumentEntity(id=d.get("id", ""), name=d.get("name", ""), document_type=d.get("document_type", ""),
                        url=d.get("url", ""), created_at=d.get("created_at", ""))
        for d in items
    ]
    return ActionResult.success(DocumentList(documents=docs), summary=f"{len(docs)} document(s).")


@chat.function(
    name="list_websites",
    description="List websites Middesk associated with a Business, with basic web-presence signals.",
)
async def list_websites(ctx, params: ListWebsitesParams) -> ActionResult[WebsiteList]:
    """List websites Middesk associated with a Business, with basic web-presence signals."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", f"/businesses/{params.business_id}/websites", action="list_websites")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    items = body.get("data", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    sites = [WebsiteEntity(id=w.get("id", ""), url=w.get("url", ""), status=w.get("status", "")) for w in items]
    return ActionResult.success(WebsiteList(websites=sites), summary=f"{len(sites)} website(s).")
