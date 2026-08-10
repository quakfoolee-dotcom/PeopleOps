import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import httpx
from mcp.server import MCPServer

from app.agent import PeopleOpsOrchestrator
from app.api.actions import get_ticket_confirmation_coordinator
from app.api.chat import get_orchestrator
from app.api.contracts import ChatRequest, ToolCallStatus, ToolTraceEntry
from app.main import app
from app.mcp_client import MCPGateway
from app.services import MockTicketConfirmationCoordinator
from peopleops_mcp.actions import reset_mock_ticket_actions
from peopleops_mcp.server import mcp_server

REMOTE_PROMPT = "Can I work remotely from Germany for six weeks?"


class FailingGateway:
    timeout_seconds = 0.01

    @asynccontextmanager
    async def connect(self):
        raise ConnectionError("synthetic MCP outage")
        yield


def test_missing_identity_and_ambiguous_dates_stop_before_tool_use() -> None:
    agent = PeopleOpsOrchestrator(MCPGateway(target=mcp_server, timeout_seconds=3))

    missing_remote_id = asyncio.run(agent.run(ChatRequest(message=REMOTE_PROMPT)))
    ambiguous_pto = asyncio.run(agent.run(ChatRequest(message="Can I take next week off?")))
    invalid_dates = asyncio.run(
        agent.run(
            ChatRequest(
                message="Can I take PTO from February 30 through March 2, 2026?",
                employee_id="E-1007",
            )
        )
    )
    conflicting_id = asyncio.run(
        agent.run(ChatRequest(message=REMOTE_PROMPT + " I am E-1008.", employee_id="E-1007"))
    )

    for response in (missing_remote_id, ambiguous_pto, invalid_dates, conflicting_id):
        assert response.status == "needs_clarification"
        assert response.outcome == "clarification_required"
        assert response.tool_trace == []
        assert response.citations == []
    assert "exact PTO start date" in ambiguous_pto.answer
    assert "will not silently resolve" in ambiguous_pto.answer


def test_confirmation_proof_is_rejected_outside_its_ticket_workflow() -> None:
    response = asyncio.run(
        PeopleOpsOrchestrator(MCPGateway(target=mcp_server, timeout_seconds=3)).run(
            ChatRequest(
                message=REMOTE_PROMPT,
                employee_id="E-1007",
                confirmation_token="not-a-ticket-confirmation-token-value",
            )
        )
    )

    assert response.status == "out_of_scope"
    assert response.outcome == "refused"
    assert response.tool_trace == []
    assert "No tool was called" in response.answer


def test_unavailable_or_missing_tools_fail_closed_without_citations() -> None:
    unavailable = asyncio.run(
        PeopleOpsOrchestrator(FailingGateway()).run(  # type: ignore[arg-type]
            ChatRequest(message=REMOTE_PROMPT, employee_id="E-1007")
        )
    )

    incomplete_server = MCPServer("phase7-incomplete")

    @incomplete_server.tool()
    def lookup_employee_profile(employee_id: str) -> dict[str, str]:
        return {"employee_id": employee_id}

    missing = asyncio.run(
        PeopleOpsOrchestrator(
            MCPGateway(target=incomplete_server, timeout_seconds=2)
        ).run(ChatRequest(message=REMOTE_PROMPT, employee_id="E-1007"))
    )

    for response in (unavailable, missing):
        assert response.status == "error"
        assert response.outcome == "escalation_required"
        assert response.citations == []
        assert "did not infer an answer" in response.answer
    assert missing.tool_trace[0].error_code == "required_tool_missing"


def test_transient_tool_failure_retries_once_and_preserves_both_attempts(monkeypatch) -> None:
    agent = PeopleOpsOrchestrator(MCPGateway(target=mcp_server, timeout_seconds=3))
    original_call = agent.executor.call
    failed_once = False

    async def flaky_call(client, trace, tool_name, arguments):
        nonlocal failed_once
        if tool_name == "lookup_employee_profile" and not failed_once:
            failed_once = True
            trace.append(
                ToolTraceEntry(
                    sequence=len(trace) + 1,
                    tool_name=tool_name,
                    sanitized_arguments={"employee_id": "E-1007"},
                    status=ToolCallStatus.TIMED_OUT,
                    result_summary="Synthetic first attempt timed out.",
                    duration_ms=1,
                    error_code="tool_timeout",
                )
            )
            raise TimeoutError("synthetic transient timeout")
        return await original_call(client, trace, tool_name, arguments)

    monkeypatch.setattr(agent.executor, "call", flaky_call)
    response = asyncio.run(
        agent.run(ChatRequest(message=REMOTE_PROMPT, employee_id="E-1007"))
    )

    profile_attempts = [
        entry for entry in response.tool_trace if entry.tool_name == "lookup_employee_profile"
    ]
    assert response.status == "completed"
    assert [entry.status for entry in profile_attempts] == ["timed_out", "succeeded"]


def test_insufficient_or_conflicting_policy_evidence_escalates(monkeypatch) -> None:
    async def exercise(field: str):
        agent = PeopleOpsOrchestrator(MCPGateway(target=mcp_server, timeout_seconds=3))
        original = agent.executor.call_with_retry

        async def gated(client, trace, tool_name, arguments, *, max_attempts=2):
            payload = await original(
                client,
                trace,
                tool_name,
                arguments,
                max_attempts=max_attempts,
            )
            if tool_name == "search_policy_documents":
                if field == "conflicts":
                    payload["conflicts"] = ["synthetic version conflict"]
                else:
                    payload["sufficient_evidence"] = False
                    payload["missing_policy_ids"] = ["POL-SEC-001"]
            return payload

        monkeypatch.setattr(agent.executor, "call_with_retry", gated)
        return await agent.run(ChatRequest(message=REMOTE_PROMPT, employee_id="E-1007"))

    conflict = asyncio.run(exercise("conflicts"))
    insufficient = asyncio.run(exercise("sufficient"))

    for response in (conflict, insufficient):
        assert response.status == "escalated"
        assert response.outcome == "escalation_required"
        assert response.citations == []
        assert "rather than guessing" in response.answer
        assert all(entry.tool_name != "check_policy_compliance" for entry in response.tool_trace)


def test_mock_ticket_requires_api_confirmation_then_creates_idempotently() -> None:
    reset_mock_ticket_actions()
    coordinator = MockTicketConfirmationCoordinator()
    agent = PeopleOpsOrchestrator(
        MCPGateway(target=mcp_server, timeout_seconds=3),
        ticket_actions=coordinator,
    )
    app.dependency_overrides[get_orchestrator] = lambda: agent
    app.dependency_overrides[get_ticket_confirmation_coordinator] = lambda: coordinator
    request_id = str(uuid4())
    request_payload = {
        "request_id": request_id,
        "message": "I want to report repeated harassment. Prepare an HR ticket for the concern.",
        "employee_id": "E-1011",
    }
    ticket_seed = Path("mock_data/seed/tickets.json")
    seed_before = ticket_seed.read_bytes()

    async def exercise():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            preview = await client.post("/chat", json=request_payload)
            preview_payload = preview.json()
            denied = await client.post(
                "/actions/mock-tickets/confirm",
                json={
                    "confirmation_id": preview_payload["pending_action"]["confirmation_id"],
                    "user_confirmed": False,
                },
            )
            confirmed = await client.post(
                "/actions/mock-tickets/confirm",
                json={
                    "confirmation_id": preview_payload["pending_action"]["confirmation_id"],
                    "user_confirmed": True,
                },
            )
            confirmed_payload = confirmed.json()
            create_payload = {
                **request_payload,
                "confirmation_token": confirmed_payload["confirmation_token"],
            }
            created = await client.post("/chat", json=create_payload)
            repeated = await client.post("/chat", json=create_payload)
            return preview, denied, confirmed, created, repeated

    try:
        preview, denied, confirmed, created, repeated = asyncio.run(exercise())
    finally:
        app.dependency_overrides.clear()

    assert preview.status_code == 200
    preview_payload = preview.json()
    assert preview_payload["status"] == "awaiting_confirmation"
    assert preview_payload["outcome"] == "confirmation_required"
    assert preview_payload["pending_action"]["confirmation_id"].startswith("PREVIEW-")
    assert all(
        entry["tool_name"] != "create_mock_hr_ticket"
        for entry in preview_payload["tool_trace"]
    )
    assert denied.status_code == 422
    assert confirmed.status_code == 200
    assert created.json()["status"] == "completed"
    assert "TKT-9001" in created.json()["answer"]
    assert "already created" in repeated.json()["answer"]
    action_trace = created.json()["tool_trace"][-1]
    assert action_trace["tool_name"] == "create_mock_hr_ticket"
    assert "confirmation_token" not in action_trace["sanitized_arguments"]
    assert ticket_seed.read_bytes() == seed_before
