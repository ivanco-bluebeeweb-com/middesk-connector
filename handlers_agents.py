"""Agents -- Middesk's AI-agent layer on top of verification (threads/
runs, with a human-in-the-loop 'interrupt policy' review gate before an
agent's final action is committed). See docs.middesk.com under Agents.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import middesk_client as mc
from handlers_connection import resolve_connection
from schemas import (
    CreateAgentThreadParams, GetAgentThreadParams, AgentThreadEntity,
    ListAgentsParams, AgentEntity, AgentList,
    RunAgentParams, AgentRunEntity, ApproveAgentRunParams,
)
from app import chat


async def _conn_or_error(ctx, connection_id: str):
    conn = await resolve_connection(ctx, connection_id)
    if not conn:
        return None, ActionResult.error("No Middesk connection is saved. Call connect_middesk first.")
    return conn, None


@chat.function(
    name="list_agents",
    description="List AI verification agents configured on the connected Middesk account.",
)
async def list_agents(ctx, params: ListAgentsParams) -> ActionResult[AgentList]:
    """List AI verification agents configured on the connected Middesk account."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", "/agents", action="list_agents")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    items = body.get("data", []) if isinstance(body, dict) else (body if isinstance(body, list) else [])
    agents = [AgentEntity(id=a.get("id", ""), name=a.get("name", ""), description=a.get("description", "")) for a in items]
    return ActionResult.success(AgentList(agents=agents), summary=f"{len(agents)} agent(s).")


@chat.function(
    name="create_agent_thread",
    description="Start a new conversation thread with a Middesk AI verification agent, optionally grounded on a specific Business.",
    action_type="write",
    effects=["create:agent_thread"],
    event="middesk-connector.create_agent_thread",
)
async def create_agent_thread(ctx, params: CreateAgentThreadParams) -> ActionResult[AgentThreadEntity]:
    """Start a new conversation thread with a Middesk AI verification agent."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    payload: dict = {"agent_id": params.agent_id.strip()}
    if params.business_id.strip():
        payload["business_id"] = params.business_id.strip()
    try:
        body = await mc.request(ctx, conn, "POST", "/threads", json_body=payload, action="create_agent_thread")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    thread = AgentThreadEntity(
        id=body.get("id", "") if isinstance(body, dict) else "",
        agent_id=params.agent_id, business_id=params.business_id,
        status=body.get("status", "") if isinstance(body, dict) else "",
    )
    return ActionResult.success(thread, summary="Agent thread started.")


@chat.function(
    name="get_agent_thread",
    description="Read one agent conversation thread in full, including its recent runs.",
)
async def get_agent_thread(ctx, params: GetAgentThreadParams) -> ActionResult[AgentThreadEntity]:
    """Read one agent conversation thread's current status."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        body = await mc.request(ctx, conn, "GET", f"/threads/{params.thread_id}", action="get_agent_thread")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    thread = AgentThreadEntity(
        id=body.get("id", params.thread_id) if isinstance(body, dict) else params.thread_id,
        agent_id=body.get("agent_id", "") if isinstance(body, dict) else "",
        business_id=body.get("business_id", "") if isinstance(body, dict) else "",
        status=body.get("status", "") if isinstance(body, dict) else "",
    )
    return ActionResult.success(thread, summary=f"Agent thread '{params.thread_id}'.")


@chat.function(
    name="run_agent",
    description="Trigger a run on an agent thread with an instruction -- the agent works the verification task and may pause at an interrupt policy step for human approval.",
    action_type="write",
    effects=["create:agent_run"],
    event="middesk-connector.run_agent",
)
async def run_agent(ctx, params: RunAgentParams) -> ActionResult[AgentRunEntity]:
    """Trigger a run on an agent thread with an instruction -- the agent works the verification task and may pause at an interrupt policy step for human approval."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    payload = {"instruction": params.instruction.strip()}
    try:
        body = await mc.request(ctx, conn, "POST", f"/threads/{params.thread_id}/runs", json_body=payload, action="run_agent")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    run = AgentRunEntity(
        id=body.get("id", ""), thread_id=params.thread_id, status=body.get("status", ""),
        requires_approval=bool(body.get("requires_approval", False)),
        output=body.get("output", ""),
    )
    return ActionResult.success(run, summary=f"Agent run '{run.status}'.")


@chat.function(
    name="approve_agent_run",
    description="Approve or reject an agent run that is paused at a human-in-the-loop interrupt policy step, letting it proceed or stopping it.",
    action_type="write",
    effects=["update:agent_run"],
    event="middesk-connector.approve_agent_run",
)
async def approve_agent_run(ctx, params: ApproveAgentRunParams) -> ActionResult[AgentRunEntity]:
    """Approve or reject an agent run that is paused at a human-in-the-loop interrupt policy step, letting it proceed or stopping it."""
    conn, err = await _conn_or_error(ctx, params.connection_id)
    if err:
        return err
    payload = {"approved": params.approved}
    try:
        body = await mc.request(ctx, conn, "POST", f"/runs/{params.run_id}/approval", json_body=payload, action="approve_agent_run")
    except mc.ClientFail as e:
        return ActionResult.error(e.message, retryable=e.payload.get("retryable", False))
    run = AgentRunEntity(
        id=body.get("id", params.run_id), thread_id=body.get("thread_id", ""),
        status=body.get("status", ""), requires_approval=False, output=body.get("output", ""),
    )
    return ActionResult.success(run, summary=f"Agent run {'approved' if params.approved else 'rejected'}.")
