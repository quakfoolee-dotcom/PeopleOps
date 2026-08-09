import asyncio
from contextlib import asynccontextmanager
from datetime import date
from typing import Any

import httpx
from mcp.server import MCPServer

from app.agent import PeopleOpsOrchestrator
from app.api.chat import get_orchestrator
from app.api.contracts import ChatRequest
from app.main import app
from app.mcp_client import MCPGateway
from peopleops_mcp.server import mcp_server

DEMO_MESSAGE = "Can I work remotely from Germany for six weeks?"


def test_orchestrator_completes_cited_mcp_workflow_with_operational_trace() -> None:
    orchestrator = PeopleOpsOrchestrator(MCPGateway(target=mcp_server, timeout_seconds=2))

    response = asyncio.run(
        orchestrator.run(ChatRequest(message=DEMO_MESSAGE, employee_id="E-1007"))
    )

    assert response.status == "completed"
    assert response.outcome == "conditional"
    assert "not automatically approved" in response.answer
    assert "30 business days" in response.answer
    assert {citation.section_id for citation in response.citations} == {
        "INT-4",
        "INT-5",
        "INT-13",
        "RWK-5",
    }
    assert [entry.tool_name for entry in response.tool_trace] == [
        "mcp_discover_tools",
        "lookup_employee_profile",
        "search_policy_documents",
    ]
    assert all(entry.status == "succeeded" for entry in response.tool_trace)
    assert response.tool_trace[1].sanitized_arguments == {"employee_id": "E-1007"}


def test_chat_api_returns_contract_validated_response_from_mcp_workflow() -> None:
    orchestrator = PeopleOpsOrchestrator(MCPGateway(target=mcp_server, timeout_seconds=2))
    app.dependency_overrides[get_orchestrator] = lambda: orchestrator

    async def post_chat() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/chat",
                json={"message": DEMO_MESSAGE, "employee_id": "E-1007"},
            )

    try:
        response = asyncio.run(post_chat())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["outcome"] == "conditional"
    assert len(payload["citations"]) == 4
    assert [entry["sequence"] for entry in payload["tool_trace"]] == [1, 2, 3]
    assert all("token" not in entry["sanitized_arguments"] for entry in payload["tool_trace"])


class FailingGateway:
    timeout_seconds = 0.01

    @asynccontextmanager
    async def connect(self):
        raise ConnectionError("synthetic MCP outage")
        yield


def test_orchestrator_fails_closed_when_mcp_is_unavailable() -> None:
    orchestrator = PeopleOpsOrchestrator(FailingGateway())  # type: ignore[arg-type]

    response = asyncio.run(
        orchestrator.run(ChatRequest(message=DEMO_MESSAGE, employee_id="E-1007"))
    )

    assert response.status == "error"
    assert response.outcome == "escalation_required"
    assert response.citations == []
    assert "did not infer an answer" in response.answer
    assert response.tool_trace[0].status == "failed"


def test_orchestrator_fails_closed_when_required_tool_is_missing() -> None:
    incomplete_server = MCPServer("incomplete")

    @incomplete_server.tool()
    def lookup_employee_profile(employee_id: str) -> dict[str, Any]:
        return {"employee_id": employee_id}

    orchestrator = PeopleOpsOrchestrator(
        MCPGateway(target=incomplete_server, timeout_seconds=2)
    )
    response = asyncio.run(
        orchestrator.run(ChatRequest(message=DEMO_MESSAGE, employee_id="E-1007"))
    )

    assert response.status == "error"
    assert response.citations == []
    assert response.tool_trace[0].status == "failed"
    assert response.tool_trace[0].error_code == "required_tool_missing"


def test_orchestrator_clarifies_unknown_employee_without_policy_lookup() -> None:
    orchestrator = PeopleOpsOrchestrator(MCPGateway(target=mcp_server, timeout_seconds=2))

    response = asyncio.run(
        orchestrator.run(ChatRequest(message=DEMO_MESSAGE, employee_id="E-9999"))
    )

    assert response.status == "needs_clarification"
    assert response.citations == []
    assert [entry.tool_name for entry in response.tool_trace] == [
        "mcp_discover_tools",
        "lookup_employee_profile",
    ]


def test_orchestrator_rejects_missing_id_unsupported_workflow_and_wrong_date() -> None:
    orchestrator = PeopleOpsOrchestrator(MCPGateway(target=mcp_server, timeout_seconds=2))

    missing_id = asyncio.run(orchestrator.run(ChatRequest(message=DEMO_MESSAGE)))
    unsupported = asyncio.run(
        orchestrator.run(
            ChatRequest(message="How many PTO hours do I have?", employee_id="E-1007")
        )
    )
    different_trip = asyncio.run(
        orchestrator.run(
            ChatRequest(
                message="Can I work remotely from Germany for two weeks?",
                employee_id="E-1007",
            )
        )
    )
    wrong_date = asyncio.run(
        orchestrator.run(
            ChatRequest(
                message=DEMO_MESSAGE,
                employee_id="E-1007",
                as_of_date=date(2026, 9, 2),
            )
        )
    )

    assert missing_id.status == "needs_clarification"
    assert unsupported.status == "out_of_scope"
    assert different_trip.status == "out_of_scope"
    assert wrong_date.status == "needs_clarification"
    assert (
        missing_id.tool_trace
        == unsupported.tool_trace
        == different_trip.tool_trace
        == wrong_date.tool_trace
        == []
    )
