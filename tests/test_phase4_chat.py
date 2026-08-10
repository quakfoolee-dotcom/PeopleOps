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
    assert "not approval" in response.answer
    assert "30 business days" in response.answer
    assert {
        "INT-5",
        "INT-13",
        "RWK-5",
        "SEC-8",
    }.issubset({citation.section_id for citation in response.citations})
    assert all(citation.chunk_id for citation in response.citations)
    assert [entry.tool_name for entry in response.tool_trace] == [
        "mcp_discover_tools",
        "lookup_employee_profile",
        "search_policy_documents",
        "get_policy_section",
        "get_policy_section",
        "get_policy_section",
        "get_policy_section",
        "check_policy_compliance",
    ]
    assert all(entry.status == "succeeded" for entry in response.tool_trace)
    assert response.tool_trace[1].sanitized_arguments == {"employee_id": "E-1007"}


def test_use_case_hint_and_attachment_feed_the_bounded_workflow() -> None:
    orchestrator = PeopleOpsOrchestrator(MCPGateway(target=mcp_server, timeout_seconds=2))

    response = asyncio.run(
        orchestrator.run(
            ChatRequest(
                message="Please evaluate the attached travel request.",
                employee_id="E-1007",
                use_case="remote_work",
                attachment={
                    "filename": "travel-details.txt",
                    "media_type": "text/plain",
                    "extracted_text": "I plan to work from Germany for six weeks.",
                    "original_size_bytes": 46,
                    "truncated": False,
                },
            )
        )
    )

    assert response.status == "completed"
    assert response.workflow == "remote_work"
    assert response.outcome == "conditional"
    search_trace = next(
        entry for entry in response.tool_trace if entry.tool_name == "search_policy_documents"
    )
    assert "travel-details.txt" not in str(search_trace.sanitized_arguments)


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
    assert [entry["sequence"] for entry in payload["tool_trace"]] == list(range(1, 9))
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


def test_orchestrator_clarifies_incomplete_pto_and_supports_other_remote_duration() -> None:
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
    assert unsupported.status == "needs_clarification"
    assert different_trip.status == "completed"
    assert different_trip.outcome == "conditional"
    assert wrong_date.status == "needs_clarification"
    assert missing_id.tool_trace == unsupported.tool_trace == wrong_date.tool_trace == []
    assert different_trip.tool_trace
