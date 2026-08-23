"""Entity Management -- registering employers for payroll taxes, a
SEPARATE Middesk product from Business Verification with its own
lifecycle: Registration Requests -> Information Requests (Middesk asks
follow-up questions) -> Applications filed with state agencies. See
docs.middesk.com/quickstart-entity.
"""
from __future__ import annotations

import json

from imperal_sdk import ActionResult

import middesk_client as mc
from handlers_connection import resolve_connection
from schemas import (
    CreateRegistrationRequestParams, GetRegistrationRequestParams,
    ListRegistrationRequestsParams, RegistrationRequestEntity,
    RegistrationRequestList,
    ListInformationRequestsParams, InformationRequestEntity,
    InformationRequestList, AnswerInformationRequestParams,
    InformationRequestAnswerResult,
    ListJurisdictionsParams, JurisdictionEntity, JurisdictionList,
    ListMailParams, MailEntity, MailList,
)
from app import chat


async def _conn_or_error(ctx, connection_id: str):
    conn = await resolve_connection(ctx, connection_id)
    if not conn:
        return None, ActionResult.error("No Middesk connection is saved. Call connect_middesk first.")
    return conn, None


def _reg_request_from_body(body: dict) -> RegistrationRequestEntity:
    return RegistrationRequestEntity(
        id=body.get("id", ""), company_id=body.get("company_id", ""),
        status=body.get("status", ""), jurisdictions=body.get("jurisdictions") or [],
        created_at=body.get("created_at", ""),
    )


@chat.function(
    name="create_registration_request",
    description="Create a payroll-tax Registration Request for a company in one or more jurisdictions (Entity Management -- separate from KYB Business Verification).",
    action_type="write",
    effects=["create:registration_request"],
    event="middesk-connector.create_registration_request",
)
async def create_registration_request(ctx, params: CreateRegistrationRequestParams) -> ActionResult[RegistrationRequestEntity]:
    """Create a payroll-tax Registration Request for a company in one or more jurisdictions (Entity Management -- separate from KYB Business Verification)."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        jurisdictions = json.loads(params.jurisdictions_json)
    except (TypeError, ValueError):
        return ActionResult.error("jurisdictions_json must be valid JSON, e.g. '[\"CA\",\"NY\"]'.")
    if not isinstance(jurisdictions, list) or not jurisdictions:
        return ActionResult.error("jurisdictions_json must decode to a non-empty JSON array of state codes.")
    payload = {"company_id": params.company_id.strip(), "jurisdictions": jurisdictions}
    try:
        body = await mc.request(ctx, conn, "POST", "/registration_requests", json_body=payload, action="create_registration_request")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    return ActionResult.success(_reg_request_from_body(body), summary="Registration request created.")


@chat.function(
    name="get_registration_request",
    description="Read one payroll-tax Registration Request in full -- status and which jurisdictions it covers.",
)
async def get_registration_request(ctx, params: GetRegistrationRequestParams) -> ActionResult[RegistrationRequestEntity]:
    """Read one payroll-tax Registration Request in full -- status and which jurisdictions it covers."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", f"/registration_requests/{params.registration_request_id}", action="get_registration_request")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    return ActionResult.success(_reg_request_from_body(body), summary=f"Registration request '{params.registration_request_id}'.")


@chat.function(
    name="list_registration_requests",
    description="List payroll-tax Registration Requests on the connected Middesk Entity Management account.",
)
async def list_registration_requests(ctx, params: ListRegistrationRequestsParams) -> ActionResult[RegistrationRequestList]:
    """List payroll-tax Registration Requests on the connected Middesk Entity Management account."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", "/registration_requests", action="list_registration_requests")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    items = body.get("data", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    reqs = [_reg_request_from_body(r) for r in items]
    return ActionResult.success(RegistrationRequestList(requests=reqs), summary=f"{len(reqs)} registration request(s).")


@chat.function(
    name="list_information_requests",
    description="List Information Requests Middesk raised while processing a Registration Request -- follow-up questions that need answers before the state application can be filed.",
)
async def list_information_requests(ctx, params: ListInformationRequestsParams) -> ActionResult[InformationRequestList]:
    """List Information Requests Middesk raised while processing a Registration Request -- follow-up questions that need answers before the state application can be filed."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", f"/registration_requests/{params.registration_request_id}/information_requests", action="list_information_requests")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    items = body.get("data", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    reqs = [
        InformationRequestEntity(id=r.get("id", ""), status=r.get("status", ""),
                                  questions=r.get("questions") or [])
        for r in items
    ]
    return ActionResult.success(InformationRequestList(requests=reqs), summary=f"{len(reqs)} information request(s).")


@chat.function(
    name="answer_information_request",
    description="Submit answers to an open Information Request so Middesk can continue filing the payroll-tax registration.",
    action_type="write",
    effects=["update:information_request"],
    event="middesk-connector.answer_information_request",
)
async def answer_information_request(ctx, params: AnswerInformationRequestParams) -> ActionResult[InformationRequestAnswerResult]:
    """Submit answers to an open payroll-tax registration Information Request."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        answers = json.loads(params.answers_json)
    except (TypeError, ValueError):
        return ActionResult.error("answers_json must be valid JSON, e.g. '{\"ein\":\"12-3456789\"}'.")
    try:
        body = await mc.request(ctx, conn, "POST", f"/information_requests/{params.information_request_id}/answers", json_body={"answers": answers}, action="answer_information_request")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    return ActionResult.success(
        InformationRequestAnswerResult(information_request_id=params.information_request_id, status=(body or {}).get("status", "submitted") if isinstance(body, dict) else "submitted"),
        summary="Answers submitted.",
    )


@chat.function(
    name="list_jurisdictions",
    description="List the state jurisdictions Middesk supports for payroll-tax registration.",
)
async def list_jurisdictions(ctx, params: ListJurisdictionsParams) -> ActionResult[JurisdictionList]:
    """List the state jurisdictions Middesk supports for payroll-tax registration."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", "/jurisdictions", action="list_jurisdictions")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    items = body.get("data", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    jurisdictions = [
        JurisdictionEntity(code=j.get("code", ""), name=j.get("name", ""),
                            registration_supported=bool(j.get("registration_supported", True)))
        for j in items
    ]
    return ActionResult.success(JurisdictionList(jurisdictions=jurisdictions), summary=f"{len(jurisdictions)} jurisdiction(s).")


@chat.function(
    name="list_mail",
    description="List physical mail Middesk has received on your behalf from state agencies during a payroll-tax registration, optionally filtered to one Registration Request.",
)
async def list_mail(ctx, params: ListMailParams) -> ActionResult[MailList]:
    """List physical mail Middesk has received on your behalf from state agencies during a payroll-tax registration, optionally filtered to one Registration Request."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    query = {}
    if params.registration_request_id.strip():
        query["registration_request_id"] = params.registration_request_id.strip()
    try:
        body = await mc.request(ctx, conn, "GET", "/mail", params=query, action="list_mail")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    items = body.get("data", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    mail = [
        MailEntity(id=m.get("id", ""), subject=m.get("subject", ""),
                   received_at=m.get("received_at", ""),
                   registration_request_id=m.get("registration_request_id", ""))
        for m in items
    ]
    return ActionResult.success(MailList(mail=mail), summary=f"{len(mail)} mail item(s).")
