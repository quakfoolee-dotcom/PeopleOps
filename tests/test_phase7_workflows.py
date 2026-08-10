import asyncio
from pathlib import Path

from app.agent import PeopleOpsOrchestrator
from app.agent.workflows import WorkflowMachine
from app.api.contracts import ChatRequest, WorkflowKind, WorkflowStage
from app.mcp_client import MCPGateway
from peopleops_mcp.server import mcp_server

REMOTE_PROMPT = "Can I work remotely from Germany for six weeks?"
PTO_PROMPT = (
    "Can I take PTO from September 21 through September 23, 2026? "
    "Check my balance and draft a message to my manager."
)
EXPENSE_PROMPT = "Can employee E-1014 be reimbursed for a CAD 900 home-office chair?"


def _agent() -> PeopleOpsOrchestrator:
    return PeopleOpsOrchestrator(MCPGateway(target=mcp_server, timeout_seconds=3))


def test_remote_work_state_machine_is_repeatable_cited_and_bounded() -> None:
    async def exercise():
        agent = _agent()
        request = ChatRequest(message=REMOTE_PROMPT, employee_id="E-1007")
        return [await agent.run(request) for _ in range(3)]

    responses = asyncio.run(exercise())

    assert all(response.status == "completed" for response in responses)
    assert all(response.outcome == "conditional" for response in responses)
    assert all(response.workflow == "remote_work" for response in responses)
    assert all(response.workflow_state == "respond" for response in responses)
    assert len({response.answer for response in responses}) == 1
    expected_sections = {"INT-5", "INT-13", "RWK-5", "SEC-8"}
    assert all(
        {citation.section_id for citation in response.citations} == expected_sections
        for response in responses
    )
    assert all(len(response.tool_trace) == 8 for response in responses)
    assert all(
        response.tool_trace[-1].tool_name == "check_policy_compliance"
        for response in responses
    )
    assert "not approval" in responses[0].answer
    assert "Manager" in responses[0].answer
    assert "Legal" in responses[0].answer
    summary = responses[0].decision_summary
    assert summary is not None
    assert summary.status_label == "Conditionally eligible"
    assert summary.duration_label == "42 calendar days / 30 business days"
    assert summary.category_label == "International exceptional"
    assert "Manager" in summary.required_approvals
    assert summary.clarification_needed == ["Exact travel and working dates"]
    assert summary.next_steps


def test_remote_work_can_prepare_a_real_unsent_peopleops_email_draft() -> None:
    response = asyncio.run(
        _agent().run(
            ChatRequest(
                message=f"{REMOTE_PROMPT} Draft a PeopleOps follow-up email for this request.",
                employee_id="E-1007",
            )
        )
    )

    assert response.status == "completed"
    assert response.outcome == "draft_only"
    assert response.tool_trace[-1].tool_name == "draft_hr_email"
    assert len(response.tool_trace) == 9
    assert response.email_draft is not None
    assert response.email_draft.label == "Draft - not sent"
    assert response.email_draft.recipient == "People Operations"
    assert response.email_draft.sent is False
    assert response.email_draft.persisted is False
    assert "Draft - not sent" not in response.answer


def test_pto_state_machine_checks_balance_and_returns_unsent_draft_without_mutation() -> None:
    seed_path = Path("mock_data/seed/pto_balances.json")
    seed_before = seed_path.read_bytes()

    response = asyncio.run(
        _agent().run(ChatRequest(message=PTO_PROMPT, employee_id="E-1021"))
    )

    assert response.status == "completed"
    assert response.outcome == "draft_only"
    assert response.workflow == "pto"
    assert {citation.section_id for citation in response.citations} == {"PTO-6", "PTO-7"}
    assert [entry.tool_name for entry in response.tool_trace] == [
        "mcp_discover_tools",
        "lookup_employee_profile",
        "check_pto_balance",
        "search_policy_documents",
        "get_policy_section",
        "get_policy_section",
        "check_policy_compliance",
        "draft_hr_email",
    ]
    assert "3 scheduled workdays (24.00 hours)" in response.answer
    assert "96.00 available hours" in response.answer
    assert "10 business days" in response.answer
    assert response.email_draft is not None
    assert response.email_draft.label == "Draft - not sent"
    assert response.email_draft.recipient == "Kendall Price"
    assert response.email_draft.sent is False
    assert response.email_draft.persisted is False
    assert "Draft - not sent" not in response.answer
    assert response.decision_summary is not None
    assert response.decision_summary.duration_label == "3 workdays / 24.00 hours"
    assert response.decision_summary.next_steps
    assert seed_path.read_bytes() == seed_before


def test_expense_state_machine_calculates_cap_remainder_and_approval() -> None:
    response = asyncio.run(
        _agent().run(ChatRequest(message=EXPENSE_PROMPT, employee_id="E-1014"))
    )

    assert response.status == "completed"
    assert response.outcome == "conditional"
    assert response.workflow == "expense"
    assert {citation.section_id for citation in response.citations} == {
        "EQP-4",
        "EXP-3",
        "EXP-7",
    }
    assert "CAD 500.00" in response.answer
    assert "CAD 400.00" in response.answer
    assert "Director or designated budget owner" in response.answer
    assert "not reimbursement or approval" in response.answer
    assert "accommodation" in response.answer
    assert response.decision_summary is not None
    assert response.decision_summary.duration_label == "CAD 900.00"
    assert response.decision_summary.required_approvals == [
        "Manager",
        "Director or designated budget owner",
    ]


def test_workflow_machine_rejects_invalid_transition_and_tool_budget_overrun() -> None:
    machine = WorkflowMachine(WorkflowKind.PTO, max_tool_calls=1)
    machine.transition(WorkflowStage.DISCOVER)
    machine.reserve_tool_call()

    try:
        machine.reserve_tool_call()
    except RuntimeError as error:
        assert "budget exhausted" in str(error)
    else:
        raise AssertionError("tool budget overrun was accepted")

    try:
        machine.transition(WorkflowStage.DRAFT)
    except RuntimeError as error:
        assert "invalid" in str(error)
    else:
        raise AssertionError("invalid state transition was accepted")
