from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcp import Client

from app.core.config import PROJECT_ROOT, get_settings
from app.mcp_client import MCPToolExecutor
from peopleops_mcp.actions import (
    confirm_mock_ticket_action,
    prepare_mock_ticket_action,
    reset_mock_ticket_actions,
)
from peopleops_mcp.server import PHASE6_TOOL_NAMES, mcp_server

RESULT_PATH = PROJECT_ROOT / "evaluation" / "results" / "phase6_mcp_validation.json"
SUMMARY = "Synthetic workplace concern for controlled review; no finding recorded."
IDEMPOTENCY_KEY = "request:phase6:evaluation-001"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def evaluate() -> dict[str, Any]:
    reset_mock_ticket_actions()
    tickets_path = PROJECT_ROOT / "mock_data" / "seed" / "tickets.json"
    seed_before = _sha256(tickets_path)
    preview = prepare_mock_ticket_action(
        category="workplace_concern",
        priority="high",
        summary=SUMMARY,
        affected_employee_id="E-1011",
        idempotency_key=IDEMPOTENCY_KEY,
    )
    token = confirm_mock_ticket_action(preview.confirmation_id, user_confirmed=True)
    calls = [
        ("search_policy_documents", {"query": "work remotely from Germany for six weeks"}),
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
                "summary": SUMMARY,
                "affected_employee_id": "E-1011",
                "idempotency_key": IDEMPOTENCY_KEY,
                "confirmation_token": token,
            },
        ),
    ]
    trace = []
    outputs: dict[str, dict[str, Any]] = {}
    executor = MCPToolExecutor(get_settings().tool_timeout_seconds)
    async with Client(mcp_server) as client:
        listed = await client.list_tools()
        discovered = await executor.discover(client, trace)
        for tool_name, arguments in calls:
            outputs[tool_name] = await executor.call(
                client,
                trace,
                tool_name,
                arguments,
            )
        unsigned = await client.call_tool(
            "create_mock_hr_ticket",
            {
                "category": "workplace_concern",
                "priority": "urgent",
                "summary": "Synthetic unsigned action must be refused.",
                "affected_employee_id": "E-1011",
                "idempotency_key": "request:phase6:evaluation-unsigned",
                "confirmation_token": "unsigned-confirmation-token-value-000000",
            },
        )
        repeated = await client.call_tool("create_mock_hr_ticket", calls[-1][1])

    repeated_payload = dict(repeated.structured_content or {})
    tool_results = [
        {
            "tool_name": entry.tool_name,
            "status": entry.status.value,
            "duration_ms": entry.duration_ms,
        }
        for entry in trace[1:]
    ]
    result = {
        "phase": 6,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "synthetic_as_of_date": get_settings().synthetic_as_of_date.isoformat(),
        "expected_tool_count": 8,
        "discovered_tool_count": len(discovered),
        "discovered_tools": sorted(discovered),
        "all_input_schemas_present": all(bool(tool.input_schema) for tool in listed.tools),
        "all_output_schemas_present": all(bool(tool.output_schema) for tool in listed.tools),
        "successful_tool_calls": sum(item["status"] == "succeeded" for item in tool_results),
        "tool_results": tool_results,
        "confirmation_gate_rejected_unsigned": unsigned.is_error,
        "idempotent_repeat_status": repeated_payload.get("action_status"),
        "confirmation_token_present_in_trace": any(
            "confirmation_token" in entry.sanitized_arguments for entry in trace
        ),
        "ticket_seed_unchanged": seed_before == _sha256(tickets_path),
        "created_ticket_id": outputs["create_mock_hr_ticket"]["ticket"]["ticket_id"],
    }
    result["passed"] = bool(
        discovered == PHASE6_TOOL_NAMES
        and result["all_input_schemas_present"]
        and result["all_output_schemas_present"]
        and result["successful_tool_calls"] == 8
        and result["confirmation_gate_rejected_unsigned"]
        and result["idempotent_repeat_status"] == "already_created"
        and not result["confirmation_token_present_in_trace"]
        and result["ticket_seed_unchanged"]
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the Phase 6 MCP tool suite.")
    parser.add_argument("--write", action="store_true", help="Write the committed JSON result.")
    arguments = parser.parse_args()
    result = asyncio.run(evaluate())
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if arguments.write:
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
