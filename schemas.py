"""Pydantic schemas for every Middesk Connector chat function, grouped by
domain: connection, Business Verification (core), Entity Management,
Agents, Prefill/Risk. Same shape/spirit as DocuSign/Ironclad Connector's
schemas.py -- one Params class and one Entity/Result class per function
(or a shared list wrapper), never raw dicts crossing the chat.function
boundary.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class NoParams(BaseModel):
    """Marker for chat functions that take no arguments."""
    pass


class DeleteResult(BaseModel):
    id: str
    deleted: bool = True


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------

class ConnectMiddeskParams(BaseModel):
    api_key: str = Field(..., description="Your Middesk API key (mk_test_... for sandbox, mk_live_... for production).")
    environment: str = Field("sandbox", description="Which Middesk environment this key belongs to: 'sandbox' or 'production'.")
    label: str = Field("", description="Optional friendly label for this connection, e.g. 'Underwriting prod'.")


class DisconnectMiddeskParams(BaseModel):
    connection_id: str = Field("", description="Which saved connection to disconnect. Leave empty if you only have one.")


class MiddeskConnection(BaseModel):
    id: str
    label: str
    environment: str
    masked_api_key: str
    connected_at: str = ""
    status: str = "connected"


class MiddeskConnectionList(BaseModel):
    connections: list[MiddeskConnection] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Business Verification -- Business object
# ---------------------------------------------------------------------------

class CreateBusinessParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    name: str = Field(..., description="Legal business name to verify, e.g. 'Acme Corporation'.")
    tin: str = Field("", description="Business Tax ID / EIN, e.g. '12-3456789'. Improves match accuracy.")
    addresses_json: str = Field("", description="JSON array of address objects, e.g. '[{\"address_line1\":\"123 Main St\",\"city\":\"Austin\",\"state\":\"TX\",\"postal_code\":\"78701\"}]'.")
    website: str = Field("", description="Business website URL, e.g. 'https://acme.com'.")
    external_id: str = Field("", description="Your own internal id for this business, for cross-referencing later.")
    order_types_json: str = Field("", description="JSON array of Middesk order product names to run immediately, e.g. '[\"identity\",\"tin\",\"watchlist\"]'. Leave empty to create the business without ordering yet.")


class UpdateBusinessParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id to update, e.g. 'business_abc123'.")
    name: str = Field("", description="Corrected legal business name, if it needs fixing.")
    tin: str = Field("", description="Corrected Tax ID / EIN, if it needs fixing.")
    external_id: str = Field("", description="Updated internal id for cross-referencing.")
    tags_json: str = Field("", description="JSON array of string tags to set on this business, e.g. '[\"high-risk\",\"reviewed\"]'.")


class GetBusinessParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id to read, e.g. 'business_abc123'.")


class ListBusinessesParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    status: str = Field("", description="Filter by verification status: open, pending, in_audit, in_review, approved, or rejected. Leave empty for all.")
    limit: int = Field(25, description="Maximum number of businesses to return.")


class BusinessEntity(BaseModel):
    id: str
    object: str = "business"
    name: str
    status: str
    created_at: str = ""
    updated_at: str = ""
    external_id: Optional[str] = None
    tin: Optional[str] = None
    website: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    review_id: Optional[str] = None


class BusinessList(BaseModel):
    businesses: list[BusinessEntity] = Field(default_factory=list)
    has_more: bool = False


class ListBusinessTimelineParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id whose event timeline you want to read.")


class TimelineEvent(BaseModel):
    id: str
    type: str
    created_at: str
    data_summary: str = ""


class TimelineEventList(BaseModel):
    events: list[TimelineEvent] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Business Verification -- Orders (identity/tin/watchlist/etc. products)
# ---------------------------------------------------------------------------

class CreateOrderParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id to order verification products for.")
    order_types_json: str = Field(..., description="JSON array of product names to order, e.g. '[\"identity\",\"tin\",\"watchlist\",\"industry_classification\",\"web_presence\",\"risk\"]'.")


class GetOrderParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id the order belongs to.")
    order_id: str = Field(..., description="The Middesk order id to read.")


class ListOrdersParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id whose orders you want to list.")


class OrderEntity(BaseModel):
    id: str
    object: str = "order"
    business_id: str = ""
    status: str = ""
    order_types: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class OrderList(BaseModel):
    orders: list[OrderEntity] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Business Verification -- Review & Review Tasks
# ---------------------------------------------------------------------------

class GetReviewParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id whose review you want to read.")


class ReviewTask(BaseModel):
    category: str
    key: str
    label: str = ""
    status: str = ""


class ReviewEntity(BaseModel):
    id: str
    object: str = "review"
    business_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    tasks: list[ReviewTask] = Field(default_factory=list)


class ListReviewInsightsParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id whose consolidated insights you want to read.")


class ReviewInsight(BaseModel):
    category: str
    summary: str = ""
    severity: str = ""


class ReviewInsightList(BaseModel):
    insights: list[ReviewInsight] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Business Verification -- Monitoring (Monitor object)
# ---------------------------------------------------------------------------

class CreateMonitorParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id to start continuous monitoring on.")


class GetMonitorParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id whose monitor you want to read.")


class DeleteMonitorParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id whose monitor you want to stop.")


class MonitorEntity(BaseModel):
    id: str
    object: str = "monitor"
    business_id: str = ""
    status: str = ""
    created_at: str = ""
    updated_at: str = ""


class ListMonitorEventsParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id whose monitoring events you want to read.")


class MonitorEvent(BaseModel):
    id: str
    type: str
    created_at: str
    summary: str = ""


class MonitorEventList(BaseModel):
    events: list[MonitorEvent] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Business Verification -- Liens, Registrations, TIN, Documents, Websites
# ---------------------------------------------------------------------------

class ListLiensParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id whose UCC/tax liens you want to list.")


class LienEntity(BaseModel):
    id: str
    object: str = "lien"
    lien_type: str = ""
    status: str = ""
    filing_number: str = ""
    filing_date: str = ""
    jurisdiction: str = ""


class LienList(BaseModel):
    liens: list[LienEntity] = Field(default_factory=list)


class ListRegistrationsParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id whose Secretary of State registrations you want to list.")


class RegistrationEntity(BaseModel):
    id: str
    object: str = "registration"
    state: str = ""
    status: str = ""
    entity_type: str = ""
    registration_date: str = ""
    standing: str = ""


class RegistrationList(BaseModel):
    registrations: list[RegistrationEntity] = Field(default_factory=list)


class GetTinParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id whose TIN match result you want to read.")


class TinEntity(BaseModel):
    id: str
    object: str = "tin"
    tin: str = ""
    tin_type: str = ""
    match_result: str = ""
    matched_name: str = ""


class ListDocumentsParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id whose supporting documents you want to list.")


class DocumentEntity(BaseModel):
    id: str
    object: str = "document"
    document_type: str = ""
    file_name: str = ""
    created_at: str = ""


class DocumentList(BaseModel):
    documents: list[DocumentEntity] = Field(default_factory=list)


class ListWebsitesParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id whose discovered/verified websites you want to list.")


class WebsiteEntity(BaseModel):
    id: str
    object: str = "website"
    url: str = ""
    status: str = ""


class WebsiteList(BaseModel):
    websites: list[WebsiteEntity] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Business Verification -- Business Batches, Signals, Policy Results, Actions
# ---------------------------------------------------------------------------

class CreateBusinessBatchParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    businesses_json: str = Field(..., description="JSON array of business objects to submit together, e.g. '[{\"name\":\"Acme Corp\",\"tin\":\"12-3456789\"},{\"name\":\"Beta LLC\"}]'.")
    order_types_json: str = Field("", description="JSON array of Middesk order product names to run on every business in the batch, e.g. '[\"identity\",\"watchlist\"]'. Leave empty to just create the businesses.")


class GetBusinessBatchParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    batch_id: str = Field(..., description="The Middesk business batch id to read.")


class BatchEntity(BaseModel):
    id: str
    object: str = "business_batch"
    status: str = ""
    business_ids: list[str] = Field(default_factory=list)
    created_at: str = ""


class ListSignalsParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id whose risk signals you want to list.")


class SignalEntity(BaseModel):
    id: str
    object: str = "signal"
    category: str = ""
    signal_type: str = ""
    severity: str = ""
    description: str = ""


class SignalList(BaseModel):
    signals: list[SignalEntity] = Field(default_factory=list)


class ListPolicyResultsParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id whose Policy (automated decisioning) results you want to list.")


class PolicyResultEntity(BaseModel):
    id: str
    object: str = "policy_result"
    policy_name: str = ""
    decision: str = ""
    created_at: str = ""


class PolicyResultList(BaseModel):
    results: list[PolicyResultEntity] = Field(default_factory=list)


class ListActionsParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id whose available/completed actions you want to list.")


class ActionEntity(BaseModel):
    id: str
    object: str = "action"
    action_type: str = ""
    status: str = ""
    created_at: str = ""


class ActionList(BaseModel):
    actions: list[ActionEntity] = Field(default_factory=list)


class CreateActionParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id to trigger the action against.")
    action_type: str = Field(..., description="The Middesk action type to trigger, e.g. 'reverify' or a documented action key for this business.")


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------

class CreateWebhookParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    url: str = Field(..., description="Your HTTPS endpoint that will receive Middesk webhook events, e.g. 'https://yourapp.com/webhooks/middesk'.")
    event_types_json: str = Field("", description="JSON array of event type names to subscribe to, e.g. '[\"business.updated\",\"review.completed\"]'. Leave empty to subscribe to all events.")


class GetWebhookParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    webhook_id: str = Field(..., description="The Middesk webhook id to read.")


class UpdateWebhookParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    webhook_id: str = Field(..., description="The Middesk webhook id to update.")
    url: str = Field("", description="New endpoint URL, if changing it.")
    event_types_json: str = Field("", description="New JSON array of subscribed event type names, if changing it.")


class DeleteWebhookParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    webhook_id: str = Field(..., description="The Middesk webhook id to permanently remove.")


class ListWebhooksParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")


class WebhookEntity(BaseModel):
    id: str
    object: str = "webhook"
    url: str = ""
    event_types: list[str] = Field(default_factory=list)
    status: str = ""
    created_at: str = ""


class WebhookList(BaseModel):
    webhooks: list[WebhookEntity] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Entity Management -- payroll-tax employer registration
# ---------------------------------------------------------------------------

class CreateRegistrationRequestParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    company_name: str = Field(..., description="Legal employer name to register for payroll taxes.")
    jurisdictions_json: str = Field(..., description="JSON array of state/jurisdiction codes to register in, e.g. '[\"CA\",\"NY\",\"TX\"]'.")
    external_id: str = Field("", description="Your own internal id for this registration request.")


class GetRegistrationRequestParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    registration_request_id: str = Field(..., description="The Middesk registration request id to read.")


class ListRegistrationRequestsParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    status: str = Field("", description="Filter by status, if known. Leave empty for all.")


class RegistrationRequestEntity(BaseModel):
    id: str
    object: str = "registration_request"
    company_name: str = ""
    status: str = ""
    jurisdictions: list[str] = Field(default_factory=list)
    created_at: str = ""


class RegistrationRequestList(BaseModel):
    registration_requests: list[RegistrationRequestEntity] = Field(default_factory=list)


class ListInformationRequestsParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    registration_request_id: str = Field(..., description="The Middesk registration request id whose outstanding information requests you want to list.")


class InformationRequestEntity(BaseModel):
    id: str
    object: str = "information_request"
    status: str = ""
    fields_needed: list[str] = Field(default_factory=list)


class InformationRequestList(BaseModel):
    information_requests: list[InformationRequestEntity] = Field(default_factory=list)


class AnswerInformationRequestParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    information_request_id: str = Field(..., description="The Middesk information request id you are answering.")
    answers_json: str = Field(..., description="JSON object mapping requested field names to their answer values, e.g. '{\"ein\":\"12-3456789\"}'.")


class ListJurisdictionsParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")


class JurisdictionEntity(BaseModel):
    code: str
    name: str = ""
    registration_supported: bool = True


class JurisdictionList(BaseModel):
    jurisdictions: list[JurisdictionEntity] = Field(default_factory=list)


class ListMailParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    registration_request_id: str = Field("", description="Filter mail to one registration request. Leave empty for all mail on the account.")


class MailEntity(BaseModel):
    id: str
    object: str = "mail"
    subject: str = ""
    received_at: str = ""
    registration_request_id: str = ""


class MailList(BaseModel):
    mail: list[MailEntity] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agents -- AI verification agents (threads/runs)
# ---------------------------------------------------------------------------

class CreateAgentThreadParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    agent_id: str = Field(..., description="The Middesk agent id to start a conversation thread with.")
    business_id: str = Field("", description="Optional business id to ground this thread's context in an existing verification.")


class GetAgentThreadParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    thread_id: str = Field(..., description="The Middesk agent thread id to read.")


class ListAgentsParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")


class AgentEntity(BaseModel):
    id: str
    object: str = "agent"
    name: str = ""
    description: str = ""


class AgentList(BaseModel):
    agents: list[AgentEntity] = Field(default_factory=list)


class RunAgentParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    thread_id: str = Field(..., description="The Middesk agent thread id to run.")
    instructions: str = Field("", description="Optional extra instructions for this run, e.g. what to focus verification on.")


class AgentRunEntity(BaseModel):
    id: str
    object: str = "run"
    thread_id: str = ""
    status: str = ""
    requires_review: bool = False
    output_summary: str = ""


class ApproveAgentRunParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    run_id: str = Field(..., description="The Middesk agent run id that is paused awaiting human review (interrupt policy).")
    approve: bool = Field(True, description="True to approve and let the run continue, False to reject it.")
    notes: str = Field("", description="Optional reviewer notes explaining the decision.")


# ---------------------------------------------------------------------------
# Prefill / Risk -- fast onboarding helpers
# ---------------------------------------------------------------------------

class AutocompleteIdentityParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    query: str = Field(..., description="Partial business name or identifier to autocomplete against Middesk's identity database, e.g. 'Acme Corp Aus'.")


class IdentitySuggestion(BaseModel):
    name: str
    tin: str = ""
    address: str = ""
    confidence: float = 0.0


class IdentitySuggestionList(BaseModel):
    suggestions: list[IdentitySuggestion] = Field(default_factory=list)


class SmartPopulateParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    name: str = Field(..., description="Business name to look up and auto-populate known fields for.")
    state: str = Field("", description="Optional two-letter state code to narrow the match, e.g. 'CA'.")


class SmartPopulateResult(BaseModel):
    name: str
    tin: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    industry: Optional[str] = None
    formation_state: Optional[str] = None


class RunRiskAssessmentParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    business_id: str = Field(..., description="The Middesk business id to run a fast risk assessment on.")


class RiskAssessmentResult(BaseModel):
    business_id: str
    risk_score: Optional[float] = None
    risk_level: str = ""
    factors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Value-add: portfolio-wide audit (Imperal-side, not a Middesk endpoint)
# ---------------------------------------------------------------------------

class AuditVerificationPortfolioParams(BaseModel):
    connection_id: str = Field("", description="Which Middesk connection to use. Leave empty if you only have one.")
    limit: int = Field(50, description="Maximum number of recent businesses to scan for the health report.")


class PortfolioAuditResult(BaseModel):
    total_scanned: int = 0
    approved: int = 0
    rejected: int = 0
    in_review: int = 0
    pending: int = 0
    flagged: list[dict] = Field(default_factory=list)
    stuck_over_7_days: list[str] = Field(default_factory=list)
    active_monitors: int = 0
    summary: str = ""


# ---------------------------------------------------------------------------
# Typed read-return shapes for round-trip symmetry (V23)
# ---------------------------------------------------------------------------

class ActionTriggerResult(BaseModel):
    business_id: str
    action_type: str
    status: str = ""


class InformationRequestAnswerResult(BaseModel):
    information_request_id: str
    status: str = "submitted"


class AgentThreadEntity(BaseModel):
    id: str
    agent_id: str = ""
    business_id: str = ""
    status: str = ""
