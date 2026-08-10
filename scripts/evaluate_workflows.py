from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.agent import PeopleOpsOrchestrator
from app.api.contracts import ChatRequest
from app.core.config import PROJECT_ROOT, get_settings
from app.mcp_client import MCPGateway
from app.services import MockTicketConfirmationCoordinator
from peopleops_mcp.actions import reset_mock_ticket_actions
from peopleops_mcp.server import mcp_server

RESULT_PATH = PROJECT_ROOT / "evaluation" / "results" / "phase7_workflows.json"
REMOTE_PROMPT = "Can I work remotely from Germany for six weeks?"
PTO_PROMPT = (
    "Can I take PTO from September 21 through September 23, 2026? "
    "Check my balance and draft a message to my manager."
)
EXPENSE_PROMPT = "Can employee E-1014 be reimbursed for a CAD 900 home-office chair?"
TICKET_PROMPT = (
    "Employee E-1011 reported repeated harassment. Prepare an HR ticket for the concern."
)


class FailingGateway:
    timeout_seconds = 0.01

    @asynccontextmanager
    async def connect(self):
        raise ConnectionError("synthetic evaluation outage")
        yield


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _summary(response) -> dict[str, Any]:
    return {
        "workflow": response.workflow.value,
        "status": response.status.value,
        "outcome": response.outcome.value,
        "citation_sections": sorted(
            {citation.section_id for citation in response.citations}
        ),
        "tool_names": [entry.tool_name for entry in response.tool_trace],
        "tool_call_count": len(response.tool_trace) - 1 if response.tool_trace else 0,
    }


async def evaluate() -> dict[str, Any]:
    reset_mock_ticket_actions()
    settings = get_settings()
    gateway = MCPGateway(target=mcp_server, timeout_seconds=3)
    agent = PeopleOpsOrchestrator(gateway)

    remote_request = ChatRequest(message=REMOTE_PROMPT, employee_id="E-1007")
    pto_request = ChatRequest(message=PTO_PROMPT, employee_id="E-1021")
    remote_runs = [await agent.run(remote_request) for _ in range(3)]
    pto_runs = [await agent.run(pto_request) for _ in range(3)]
    expense = await agent.run(ChatRequest(message=EXPENSE_PROMPT, employee_id="E-1014"))
    ambiguous = await agent.run(ChatRequest(message="Can I take next week off?"))
    missing_id = await agent.run(ChatRequest(message=REMOTE_PROMPT))

    unavailable = await PeopleOpsOrchestrator(FailingGateway()).run(  # type: ignore[arg-type]
        ChatRequest(message=REMOTE_PROMPT, employee_id="E-1007")
    )

    conflict_agent = PeopleOpsOrchestrator(gateway)
    original_call = conflict_agent.executor.call_with_retry

    async def inject_conflict(client, trace, tool_name, arguments, *, max_attempts=2):
        payload = await original_call(
            client,
            trace,
            tool_name,
            arguments,
            max_attempts=max_attempts,
        )
        if tool_name == "search_policy_documents":
            payload["conflicts"] = ["synthetic evaluation conflict"]
        return payload

    conflict_agent.executor.call_with_retry = inject_conflict  # type: ignore[method-assign]
    conflict = await conflict_agent.run(remote_request)

    tickets_path = PROJECT_ROOT / "mock_data" / "seed" / "tickets.json"
    ticket_seed_before = _sha256(tickets_path)
    coordinator = MockTicketConfirmationCoordinator()
    ticket_agent = PeopleOpsOrchestrator(gateway, ticket_actions=coordinator)
    ticket_request = ChatRequest(message=TICKET_PROMPT, employee_id="E-1011")
    preview = await ticket_agent.run(ticket_request)
    assert preview.pending_action is not None
    token = coordinator.confirm(
        preview.pending_action.confirmation_id or "",
        user_confirmed=True,
    )
    confirmed_request = ticket_request.model_copy(update={"confirmation_token": token})
    created = await ticket_agent.run(confirmed_request)
    repeated = await ticket_agent.run(confirmed_request)

    remote_repeatable = len({response.answer for response in remote_runs}) == 1
    pto_repeatable = len({response.answer for response in pto_runs}) == 1
    confirmation_token_in_trace = any(
        "confirmation_token" in entry.sanitized_arguments
        for response in (preview, created, repeated)
        for entry in response.tool_trace
    )
    result = {
        "phase": 7,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "synthetic_as_of_date": settings.synthetic_as_of_date.isoformat(),
        "max_logical_tool_calls": settings.max_tool_calls,
        "bounded_retry_attempts": 2,
        "remote_work": {
            "repeat_count": len(remote_runs),
            "repeatable": remote_repeatable,
            **_summary(remote_runs[0]),
        },
        "pto": {
            "repeat_count": len(pto_runs),
            "repeatable": pto_repeatable,
            "draft_not_sent": bool(
                pto_runs[0].email_draft
                and not pto_runs[0].email_draft.sent
                and not pto_runs[0].email_draft.persisted
            ),
            **_summary(pto_runs[0]),
        },
        "expense": _summary(expense),
        "safety": {
            "ambiguous_dates_clarified_without_tools": (
                ambiguous.status == "needs_clarification" and not ambiguous.tool_trace
            ),
            "missing_id_clarified_without_tools": (
                missing_id.status == "needs_clarification" and not missing_id.tool_trace
            ),
            "unavailable_mcp_failed_closed": (
                unavailable.status == "error" and not unavailable.citations
            ),
            "policy_conflict_escalated": (
                conflict.status == "escalated" and not conflict.citations
            ),
        },
        "confirmation": {
            "preview_status": preview.status.value,
            "create_called_before_confirmation": any(
                entry.tool_name == "create_mock_hr_ticket" for entry in preview.tool_trace
            ),
            "created_status": created.status.value,
            "created_ticket_id": "TKT-9001" if "TKT-9001" in created.answer else None,
            "idempotent_repeat": "already created" in repeated.answer,
            "confirmation_token_present_in_trace": confirmation_token_in_trace,
            "ticket_seed_unchanged": ticket_seed_before == _sha256(tickets_path),
        },
    }
    result["passed"] = bool(
        result["remote_work"]["repeatable"]
        and result["remote_work"]["status"] == "completed"
        and result["remote_work"]["outcome"] == "conditional"
        and result["remote_work"]["citation_sections"]
        == ["INT-13", "INT-5", "RWK-5", "SEC-8"]
        and result["pto"]["repeatable"]
        and result["pto"]["status"] == "completed"
        and result["pto"]["outcome"] == "draft_only"
        and result["pto"]["draft_not_sent"]
        and result["expense"]["status"] == "completed"
        and all(result["safety"].values())
        and result["confirmation"]["preview_status"] == "awaiting_confirmation"
        and not result["confirmation"]["create_called_before_confirmation"]
        and result["confirmation"]["created_status"] == "completed"
        and result["confirmation"]["idempotent_repeat"]
        and not result["confirmation"]["confirmation_token_present_in_trace"]
        and result["confirmation"]["ticket_seed_unchanged"]
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Phase 7 bounded workflows.")
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
