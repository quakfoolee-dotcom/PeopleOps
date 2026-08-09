import ast
import asyncio
from pathlib import Path

import pytest
from mcp import Client
from mcp.server import MCPServer

from app.api.contracts import ToolTraceEntry
from app.mcp_client import MCPToolExecutor
from peopleops_mcp.actions import (
    confirm_mock_ticket_action,
    prepare_mock_ticket_action,
    reset_mock_ticket_actions,
)
from peopleops_mcp.schemas import (
    BenefitsStatusResult,
    ComplianceCheckResult,
    EmployeeProfileResult,
    HREmailDraftResult,
    MockTicketActionResult,
    PolicySearchResult,
    PolicySectionResult,
    PTOBalanceResult,
)
from peopleops_mcp.server import PHASE6_TOOL_NAMES, mcp_server


def test_agent_layer_has_no_direct_data_rag_or_tool_implementation_imports() -> None:
    forbidden_prefixes = ("app.data", "app.rag", "peopleops_mcp.tools", "peopleops_mcp.actions")
    for source_path in Path("app/agent").glob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        assert not any(
            module.startswith(forbidden_prefixes)
            for module in imports
        ), f"{source_path} bypasses MCP: {imports}"


def test_all_eight_tools_are_discoverable_schema_valid_and_traced() -> None:
    reset_mock_ticket_actions()
    preview = prepare_mock_ticket_action(
        category="workplace_concern",
        priority="high",
        summary="Synthetic workplace concern for controlled review; no finding recorded.",
        affected_employee_id="E-1011",
        idempotency_key="request:phase6:integration-001",
    )
    token = confirm_mock_ticket_action(preview.confirmation_id, user_confirmed=True)

    async def exercise() -> tuple[list, list[ToolTraceEntry], dict[str, dict]]:
        trace: list[ToolTraceEntry] = []
        outputs: dict[str, dict] = {}
        executor = MCPToolExecutor(timeout_seconds=2)
        async with Client(mcp_server) as client:
            listed = await client.list_tools()
            discovered = await executor.discover(client, trace)
            assert discovered == PHASE6_TOOL_NAMES
            calls = [
                (
                    "search_policy_documents",
                    {"query": "Can I work remotely from Germany for six weeks?"},
                ),
                (
                    "get_policy_section",
                    {"policy_id": "POL-PTO-001", "section_id": "PTO-6"},
                ),
                ("lookup_employee_profile", {"employee_id": "E-1007"}),
                (
                    "check_pto_balance",
                    {
                        "employee_id": "E-1021",
                        "request_start": "2026-09-21",
                        "request_end": "2026-09-23",
                    },
                ),
                ("lookup_benefits_status", {"employee_id": "E-1003"}),
                (
                    "check_policy_compliance",
                    {
                        "workflow": "home_office_expense",
                        "employee_id": "E-1014",
                        "expense_amount": "900",
                        "currency": "CAD",
                    },
                ),
                (
                    "draft_hr_email",
                    {
                        "draft_type": "pto_manager_request",
                        "employee_id": "E-1021",
                        "request_start": "2026-09-21",
                        "request_end": "2026-09-23",
                    },
                ),
                (
                    "create_mock_hr_ticket",
                    {
                        "category": "workplace_concern",
                        "priority": "high",
                        "summary": (
                            "Synthetic workplace concern for controlled review; "
                            "no finding recorded."
                        ),
                        "affected_employee_id": "E-1011",
                        "idempotency_key": "request:phase6:integration-001",
                        "confirmation_token": token,
                    },
                ),
            ]
            for tool_name, arguments in calls:
                outputs[tool_name] = await executor.call(
                    client,
                    trace,
                    tool_name,
                    arguments,
                )
        return listed.tools, trace, outputs

    tools, trace, outputs = asyncio.run(exercise())

    assert {tool.name for tool in tools} == PHASE6_TOOL_NAMES
    assert all(tool.input_schema for tool in tools)
    assert all(tool.output_schema for tool in tools)
    assert [entry.sequence for entry in trace] == list(range(1, 10))
    assert [entry.tool_name for entry in trace[1:]] == sorted(
        PHASE6_TOOL_NAMES,
        key=lambda name: [
            "search_policy_documents",
            "get_policy_section",
            "lookup_employee_profile",
            "check_pto_balance",
            "lookup_benefits_status",
            "check_policy_compliance",
            "draft_hr_email",
            "create_mock_hr_ticket",
        ].index(name),
    )
    assert all(entry.status == "succeeded" for entry in trace)
    action_trace = trace[-1]
    assert "confirmation_token" not in action_trace.sanitized_arguments
    assert action_trace.sanitized_arguments["summary"].startswith("[redacted:")

    PolicySearchResult.model_validate(outputs["search_policy_documents"])
    PolicySectionResult.model_validate(outputs["get_policy_section"])
    EmployeeProfileResult.model_validate(outputs["lookup_employee_profile"])
    PTOBalanceResult.model_validate(outputs["check_pto_balance"])
    BenefitsStatusResult.model_validate(outputs["lookup_benefits_status"])
    ComplianceCheckResult.model_validate(outputs["check_policy_compliance"])
    HREmailDraftResult.model_validate(outputs["draft_hr_email"])
    action = MockTicketActionResult.model_validate(outputs["create_mock_hr_ticket"])
    assert action.action_status == "created"


def test_create_tool_rejects_unsigned_or_unconfirmed_action() -> None:
    async def exercise():
        async with Client(mcp_server) as client:
            return await client.call_tool(
                "create_mock_hr_ticket",
                {
                    "category": "workplace_concern",
                    "priority": "urgent",
                    "summary": "Synthetic concern requiring controlled review.",
                    "affected_employee_id": "E-1011",
                    "idempotency_key": "request:phase6:unsigned-001",
                    "confirmation_token": "unsigned-confirmation-token-value-000000",
                },
            )

    result = asyncio.run(exercise())

    assert result.is_error is True
    assert result.structured_content is None


def test_executor_enforces_timeout_and_records_failure_trace() -> None:
    slow_server = MCPServer("phase6-timeout-test")

    @slow_server.tool()
    async def slow_tool() -> dict[str, bool]:
        await asyncio.sleep(0.1)
        return {"completed": True}

    async def exercise() -> list[ToolTraceEntry]:
        trace: list[ToolTraceEntry] = []
        executor = MCPToolExecutor(timeout_seconds=0.01)
        async with Client(slow_server) as client:
            with pytest.raises(TimeoutError):
                await executor.call(client, trace, "slow_tool", {})
        return trace

    trace = asyncio.run(exercise())

    assert len(trace) == 1
    assert trace[0].tool_name == "slow_tool"
    assert trace[0].status == "timed_out"
    assert trace[0].error_code == "tool_timeout"
