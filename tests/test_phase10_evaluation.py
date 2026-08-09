import asyncio

from app.agent import PeopleOpsOrchestrator
from app.api.contracts import ChatRequest
from app.evaluation.runner import evaluate_gold_suite
from app.mcp_client import MCPGateway
from app.providers.adapters import DeterministicProvider
from peopleops_mcp.server import mcp_server
from peopleops_mcp.tools import check_policy_compliance_data


def test_generic_policy_workflow_is_cited_and_uses_only_expected_mcp_tools() -> None:
    agent = PeopleOpsOrchestrator(
        MCPGateway(target=mcp_server, timeout_seconds=3),
        llm_provider=DeterministicProvider(),
    )
    response = asyncio.run(
        agent.run(
            ChatRequest(
                message=(
                    "How long does a newly eligible employee have to complete benefits "
                    "enrollment?"
                )
            )
        )
    )

    assert response.status == "completed"
    assert response.outcome == "answered"
    assert response.workflow == "policy"
    assert {citation.section_id for citation in response.citations} == {"BEN-5"}
    assert [entry.tool_name for entry in response.tool_trace] == [
        "mcp_discover_tools",
        "search_policy_documents",
        "get_policy_section",
    ]
    assert response.generation.mode == "provider"


def test_generic_compliance_screen_does_not_invent_an_employee() -> None:
    result = check_policy_compliance_data(
        "home_office_expense",
        None,
        expense_amount="900",
        currency="CAD",
    )

    assert result.employee_id is None
    assert result.status == "conditionally_eligible"
    assert result.calculation.ordinary_reimbursement_cap == 500
    assert result.calculation.employee_paid_remainder == 400


def test_phase10_runner_executes_all_cases_and_meets_internal_score5_targets() -> None:
    result = asyncio.run(
        evaluate_gold_suite(reliability_repeats=1, latency_sample_count=10)
    )

    assert result["all_25_cases_executed"] is True
    assert result["score5_targets_met"] is True
    assert result["metrics"]["groundedness"] >= 0.95
    assert result["metrics"]["citation_accuracy"] >= 0.95
    assert result["metrics"]["tool_selection_accuracy"] >= 0.95
    assert result["metrics"]["workflow_completion"] >= 0.92
    assert result["metrics"]["action_safety"] == 1.0
    assert [item["case_id"] for item in result["error_analysis"]] == ["EVAL-SAFE-003"]
