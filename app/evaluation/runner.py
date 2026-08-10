from __future__ import annotations

import json
import statistics
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from app.agent import PeopleOpsOrchestrator
from app.api.contracts import ChatRequest, WorkflowOutcome, WorkflowStatus
from app.evaluation.answer_quality import (
    evaluate_answer_quality,
    load_answer_check_suite,
)
from app.evaluation.contracts import (
    CaseAnswerChecks,
    GoldEvaluationCase,
    GoldEvaluationSuite,
)
from app.mcp_client import MCPGateway
from app.providers.adapters import DeterministicProvider
from app.services import MockTicketConfirmationCoordinator
from peopleops_mcp.actions import reset_mock_ticket_actions
from peopleops_mcp.server import mcp_server

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GOLD_SUITE_PATH = PROJECT_ROOT / "evaluation" / "gold_cases.json"
ABLATION_PATH = PROJECT_ROOT / "evaluation" / "results" / "phase5_rag_ablation.json"
INTERNAL_TRACE_TOOLS = frozenset({"mcp_discover_tools", "prepare_mock_ticket_preview"})
TARGETS = {
    "groundedness": 0.95,
    "answer_fact_accuracy": 0.95,
    "answer_constraint_adherence": 0.95,
    "claim_citation_support": 0.95,
    "citation_accuracy": 0.95,
    "retrieval_evidence_recall": 0.95,
    "tool_selection_accuracy": 0.95,
    "workflow_completion": 0.92,
    "clarification_escalation_accuracy": 0.90,
    "action_safety": 1.0,
    "primary_demo_completion": 1.0,
}


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 1.0


def _percentile(values: list[int], quantile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    rank = max(1, round(quantile * len(ordered)))
    return ordered[min(rank - 1, len(ordered) - 1)]


def _tool_names(response: Any) -> list[str]:
    return [
        entry.tool_name
        for entry in response.tool_trace
        if entry.tool_name not in INTERNAL_TRACE_TOOLS
    ]


def _expected_sections(case: GoldEvaluationCase) -> set[tuple[str, str]]:
    return {
        (section.policy_id, section.section_id)
        for section in case.expected_policy_sections
    }


def _returned_sections(response: Any) -> set[tuple[str, str]]:
    return {(citation.policy_id, citation.section_id) for citation in response.citations}


def _selected_ablation() -> dict[str, Any]:
    payload = json.loads(ABLATION_PATH.read_text(encoding="utf-8"))
    selected = next(
        item
        for item in payload["configurations"]
        if item["mode"] == "hybrid" and item["top_k"] == 8
    )
    return {
        "mode": selected["mode"],
        "top_k": selected["top_k"],
        "evidence_recall": selected["evidence_recall"],
        "expected_sections": selected["expected_sections"],
        "retrieved_expected_sections": selected["retrieved_expected_sections"],
        "latency_ms": selected["latency_ms"],
    }


async def _run_case(
    case: GoldEvaluationCase,
    answer_checks: CaseAnswerChecks,
    agent: PeopleOpsOrchestrator,
    coordinator: MockTicketConfirmationCoordinator,
) -> dict[str, Any]:
    request = ChatRequest(message=case.prompt, employee_id=case.employee_id)
    started = perf_counter()
    response = await agent.run(request)
    duration_ms = max(0, round((perf_counter() - started) * 1000))

    actual_tools = _tool_names(response)
    actual_tool_set = set(actual_tools)
    required_tools = set(case.tools.required)
    forbidden_tools = set(case.tools.forbidden)
    after_confirmation_tools = set(case.tools.after_confirmation)
    returned_sections = _returned_sections(response)
    expected_sections = _expected_sections(case)
    expects_citations = "get_policy_section" in required_tools

    required_tools_covered = required_tools <= actual_tool_set
    forbidden_tools_avoided = not (forbidden_tools & actual_tool_set)
    confirmation_tools_deferred = not (after_confirmation_tools & actual_tool_set)
    unexpected_tools = actual_tool_set - required_tools
    tool_selection_pass = (
        required_tools_covered
        and forbidden_tools_avoided
        and confirmation_tools_deferred
        and not unexpected_tools
    )

    expected_citations_covered = not expects_citations or expected_sections <= returned_sections
    citations_exact = returned_sections <= expected_sections
    outcome_match = response.outcome is case.expected_outcome
    workflow_complete = outcome_match and response.status is not WorkflowStatus.ERROR
    answer_quality = evaluate_answer_quality(
        case,
        answer_checks,
        response,
        actual_tool_set,
    )
    grounded = bool(
        workflow_complete
        and expected_citations_covered
        and citations_exact
        and required_tools_covered
        and answer_quality["passed"]
    )

    confirmation: dict[str, Any] | None = None
    action_safe = True
    if after_confirmation_tools:
        create_before_confirmation = bool(after_confirmation_tools & actual_tool_set)
        action_safe = not create_before_confirmation
        confirmation = {
            "preview_returned": response.pending_action is not None,
            "create_before_confirmation": create_before_confirmation,
            "after_confirmation_tools": [],
            "idempotent_repeat": False,
            "confirmation_token_in_trace": False,
        }
        if response.pending_action is not None:
            token = coordinator.confirm(
                response.pending_action.confirmation_id,
                user_confirmed=True,
            )
            confirmed_request = request.model_copy(update={"confirmation_token": token})
            confirmed = await agent.run(confirmed_request)
            repeated = await agent.run(confirmed_request)
            confirmed_tools = _tool_names(confirmed)
            token_in_trace = any(
                "confirmation_token" in entry.sanitized_arguments
                for entry in confirmed.tool_trace
            )
            confirmation.update(
                {
                    "after_confirmation_tools": confirmed_tools,
                    "after_confirmation_tools_covered": (
                        after_confirmation_tools <= set(confirmed_tools)
                    ),
                    "idempotent_repeat": "already created" in repeated.answer,
                    "confirmation_token_in_trace": token_in_trace,
                }
            )
            action_safe = bool(
                action_safe
                and after_confirmation_tools <= set(confirmed_tools)
                and "already created" in repeated.answer
                and not token_in_trace
            )

    failures = []
    if not outcome_match:
        failures.append(
            f"outcome={response.outcome.value}, expected={case.expected_outcome.value}"
        )
    if not required_tools_covered:
        failures.append(
            "missing required tools: " + ", ".join(sorted(required_tools - actual_tool_set))
        )
    if not forbidden_tools_avoided:
        failures.append(
            "called forbidden tools: " + ", ".join(sorted(forbidden_tools & actual_tool_set))
        )
    if unexpected_tools:
        failures.append("unexpected tools: " + ", ".join(sorted(unexpected_tools)))
    if not expected_citations_covered:
        missing = expected_sections - returned_sections
        failures.append(
            "missing expected citations: "
            + ", ".join(f"{policy}:{section}" for policy, section in sorted(missing))
        )
    if not citations_exact:
        unexpected = returned_sections - expected_sections
        failures.append(
            "unexpected citations: "
            + ", ".join(f"{policy}:{section}" for policy, section in sorted(unexpected))
        )
    for index, result in enumerate(answer_quality["fact_results"], start=1):
        if not result["content_pass"]:
            failures.append(f"expected fact {index} not established: {result['detail']}")
        if not result["support_pass"]:
            failures.append(
                f"expected fact {index} lacks declared evidence support: {result['support']}"
            )
    for index, result in enumerate(answer_quality["constraint_results"], start=1):
        if not result["passed"]:
            failures.append(f"answer constraint {index} failed: {result['detail']}")

    return {
        "case_id": case.case_id,
        "title": case.title,
        "category": case.category.value,
        "prompt": case.prompt,
        "expected_outcome": case.expected_outcome.value,
        "actual_outcome": response.outcome.value,
        "status": response.status.value,
        "workflow": response.workflow.value,
        "duration_ms": duration_ms,
        "generation_mode": response.generation.mode,
        "tools": actual_tools,
        "required_tools": sorted(required_tools),
        "returned_sections": [
            f"{policy}:{section}" for policy, section in sorted(returned_sections)
        ],
        "expected_sections": [
            f"{policy}:{section}" for policy, section in sorted(expected_sections)
        ],
        "outcome_match": outcome_match,
        "tool_selection_pass": tool_selection_pass,
        "citation_coverage_pass": expected_citations_covered,
        "citation_accuracy_pass": citations_exact,
        "groundedness_pass": grounded,
        "answer_fact_accuracy_pass": answer_quality["answer_fact_accuracy_pass"],
        "answer_constraint_pass": answer_quality["answer_constraint_pass"],
        "claim_citation_support_pass": answer_quality["claim_citation_support_pass"],
        "answer_quality": answer_quality,
        "workflow_completion_pass": workflow_complete,
        "action_safety_pass": action_safe,
        "confirmation": confirmation,
        "answer": response.answer,
        "request_id": str(response.request_id),
        "trace_id": str(response.trace_id),
        "failures": failures,
    }


async def _primary_reliability(
    suite: GoldEvaluationSuite,
    agent: PeopleOpsOrchestrator,
    repeat_count: int,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for case in (item for item in suite.cases if "primary-demo" in item.tags):
        runs = []
        for _ in range(repeat_count):
            response = await agent.run(
                ChatRequest(message=case.prompt, employee_id=case.employee_id)
            )
            runs.append(response)
        result[case.case_id] = {
            "repeat_count": repeat_count,
            "completion_rate": _ratio(
                sum(
                    response.outcome is case.expected_outcome
                    and response.status is WorkflowStatus.COMPLETED
                    for response in runs
                ),
                repeat_count,
            ),
            "repeatable_verified_result": len(
                {
                    response.answer.split("Verified workflow result\n")[-1]
                    for response in runs
                }
            )
            == 1,
        }
    return result


async def evaluate_gold_suite(
    *,
    reliability_repeats: int = 10,
    latency_sample_count: int = 20,
) -> dict[str, Any]:
    if not 1 <= reliability_repeats <= 20:
        raise ValueError("reliability_repeats must be between 1 and 20")
    if not 10 <= latency_sample_count <= 20:
        raise ValueError("latency_sample_count must be between 10 and 20")

    suite = GoldEvaluationSuite.model_validate_json(
        GOLD_SUITE_PATH.read_text(encoding="utf-8")
    )
    checks_by_case = {
        item.case_id: item for item in load_answer_check_suite().cases
    }
    reset_mock_ticket_actions()
    coordinator = MockTicketConfirmationCoordinator()
    agent = PeopleOpsOrchestrator(
        MCPGateway(target=mcp_server, timeout_seconds=5),
        ticket_actions=coordinator,
        llm_provider=DeterministicProvider(),
    )

    cold_case = next(item for item in suite.cases if item.case_id == "EVAL-TOOL-001")
    cold_started = perf_counter()
    cold_response = await agent.run(
        ChatRequest(message=cold_case.prompt, employee_id=cold_case.employee_id)
    )
    cold_latency_ms = max(0, round((perf_counter() - cold_started) * 1000))

    case_results = [
        await _run_case(case, checks_by_case[case.case_id], agent, coordinator)
        for case in suite.cases
    ]
    reliability = await _primary_reliability(
        suite,
        agent,
        reliability_repeats,
    )

    total = len(case_results)
    citation_results = [item for item in case_results if item["returned_sections"]]
    clarification_or_escalation = [
        item
        for item in case_results
        if item["expected_outcome"]
        in {
            WorkflowOutcome.CLARIFICATION_REQUIRED.value,
            WorkflowOutcome.ESCALATION_REQUIRED.value,
            WorkflowOutcome.REFUSED.value,
        }
    ]
    action_cases = [item for item in case_results if item["confirmation"] is not None]
    primary_case_ids = {
        case.case_id for case in suite.cases if "primary-demo" in case.tags
    }
    primary_cases = [
        item for item in case_results if item["case_id"] in primary_case_ids
    ]
    warm_samples = [
        item["duration_ms"] for item in case_results[:latency_sample_count]
    ]
    ablation = _selected_ablation()
    metrics = {
        "executed_cases": total,
        "groundedness": _ratio(
            sum(item["groundedness_pass"] for item in case_results), total
        ),
        "answer_fact_accuracy": _ratio(
            sum(item["answer_fact_accuracy_pass"] for item in case_results), total
        ),
        "answer_constraint_adherence": _ratio(
            sum(item["answer_constraint_pass"] for item in case_results), total
        ),
        "claim_citation_support": _ratio(
            sum(item["claim_citation_support_pass"] for item in case_results), total
        ),
        "citation_accuracy": _ratio(
            sum(item["citation_accuracy_pass"] for item in citation_results),
            len(citation_results),
        ),
        "citation_coverage": _ratio(
            sum(item["citation_coverage_pass"] for item in case_results), total
        ),
        "retrieval_evidence_recall": ablation["evidence_recall"],
        "tool_selection_accuracy": _ratio(
            sum(item["tool_selection_pass"] for item in case_results), total
        ),
        "workflow_completion": _ratio(
            sum(item["workflow_completion_pass"] for item in case_results), total
        ),
        "clarification_escalation_accuracy": _ratio(
            sum(item["workflow_completion_pass"] for item in clarification_or_escalation),
            len(clarification_or_escalation),
        ),
        "action_safety": _ratio(
            sum(item["action_safety_pass"] for item in action_cases),
            len(action_cases),
        ),
        "primary_demo_completion": _ratio(
            sum(item["workflow_completion_pass"] for item in primary_cases),
            len(primary_cases),
        ),
        "latency_ms": {
            "local_cold_primary": cold_latency_ms,
            "local_cold_outcome": cold_response.outcome.value,
            "warm_sample_count": len(warm_samples),
            "warm_p50": round(statistics.median(warm_samples)),
            "warm_p95": _percentile(warm_samples, 0.95),
            "warm_min": min(warm_samples),
            "warm_max": max(warm_samples),
        },
    }
    target_checks = {
        name: metrics[name] >= threshold
        for name, threshold in TARGETS.items()
    }
    reliability_pass = all(
        item["completion_rate"] == 1.0 and item["repeatable_verified_result"]
        for item in reliability.values()
    )
    errors = [
        {
            "case_id": item["case_id"],
            "title": item["title"],
            "failures": item["failures"],
        }
        for item in case_results
        if item["failures"]
    ]
    return {
        "phase": 10,
        "suite": suite.name,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "synthetic_as_of_date": suite.as_of_date.isoformat(),
        "provider": "deterministic-grounded-v1",
        "methodology": {
            "groundedness": (
                "A response passes when its expected outcome completes, required tools and exact "
                "gold citations are present, every expected fact is asserted, every answer "
                "constraint passes, and each factual claim has declared source or tool support."
            ),
            "answer_quality": (
                "Each expected fact and answer constraint has a versioned executable assertion. "
                "Fact support requires the declared policy sections or structured tools; policy "
                "claims additionally require lexical and numeric agreement with returned snippets."
            ),
            "citation_accuracy": (
                "Case-level exactness: every displayed policy/section pair belongs to the gold "
                "evidence set and passed the runtime authoritative-index validator."
            ),
            "tool_selection": (
                "All required tools must run, forbidden and post-confirmation tools must not run "
                "early, and no unplanned domain tool may run. Discovery and local preview tracing "
                "are control-plane events."
            ),
            "latency": (
                "Cold is the first in-process primary workflow. Warm p50/p95 uses the first "
                f"{latency_sample_count} gold cases after that warm-up; provider calls use the "
                "deterministic CI adapter. Hosted Render cold/warm timing is reported separately."
            ),
        },
        "targets": TARGETS,
        "metrics": metrics,
        "target_checks": target_checks,
        "primary_reliability": reliability,
        "retrieval_ablation_selected": ablation,
        "score5_targets_met": all(target_checks.values()) and reliability_pass,
        "all_25_cases_executed": total == 25,
        "error_analysis": errors,
        "cases": case_results,
    }
