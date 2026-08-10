import asyncio

from app.agent import PeopleOpsOrchestrator
from app.api.contracts import ChatRequest
from app.evaluation.answer_quality import evaluate_answer_quality, load_answer_check_suite
from app.evaluation.gold import load_gold_suite
from app.mcp_client import MCPGateway
from app.providers.adapters import DeterministicProvider
from peopleops_mcp.server import mcp_server


def test_expected_fact_assertions_reject_a_structurally_grounded_but_empty_answer() -> None:
    case = next(item for item in load_gold_suite().cases if item.case_id == "EVAL-POL-002")
    checks = next(
        item for item in load_answer_check_suite().cases if item.case_id == case.case_id
    )
    agent = PeopleOpsOrchestrator(
        MCPGateway(target=mcp_server, timeout_seconds=3),
        llm_provider=DeterministicProvider(),
    )
    response = asyncio.run(
        agent.run(ChatRequest(message=case.prompt, employee_id=case.employee_id))
    )
    tools = {entry.tool_name for entry in response.tool_trace}

    passing = evaluate_answer_quality(case, checks, response, tools)
    altered = response.model_copy(update={"answer": "The workflow completed."})
    failing = evaluate_answer_quality(case, checks, altered, tools)

    assert passing["passed"] is True
    assert failing["answer_fact_accuracy_pass"] is False
    assert failing["passed"] is False
