from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api.contracts import ChatResponse  # noqa: E402

RESULT_PATH = PROJECT_ROOT / "evaluation" / "results" / "phase10_hosted_provider.json"
DEFAULT_BASE_URL = "https://peopleops-assistant-demo.onrender.com"
CASES = (
    {
        "case_id": "HOSTED-PROVIDER-001",
        "prompt": "How long does a newly eligible employee have to complete benefits enrollment?",
        "employee_id": None,
        "workflow": "policy",
        "outcome": "answered",
        "sections": {"BEN-5"},
        "tools": {"search_policy_documents", "get_policy_section"},
    },
    {
        "case_id": "HOSTED-PROVIDER-002",
        "prompt": (
            "A British Columbia employee wants to work from Germany for six weeks. What "
            "approvals and conditions apply?"
        ),
        "employee_id": None,
        "workflow": "policy",
        "outcome": "conditional",
        "sections": {"INT-5", "INT-13", "RWK-5", "SEC-8"},
        "tools": {
            "search_policy_documents",
            "get_policy_section",
            "check_policy_compliance",
        },
    },
    {
        "case_id": "HOSTED-PROVIDER-003",
        "prompt": (
            "Can an otherwise eligible remote employee be reimbursed for a CAD 900 "
            "home-office chair?"
        ),
        "employee_id": None,
        "workflow": "policy",
        "outcome": "conditional",
        "sections": {"EQP-4", "EXP-3", "EXP-7"},
        "tools": {
            "search_policy_documents",
            "get_policy_section",
            "check_policy_compliance",
        },
    },
)


def _p95(values: list[int]) -> int:
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, round(0.95 * len(ordered)) - 1))]


def evaluate(base_url: str, timeout_seconds: float) -> dict[str, Any]:
    with httpx.Client(
        base_url=base_url.rstrip("/"),
        timeout=httpx.Timeout(timeout_seconds),
        follow_redirects=True,
        headers={"User-Agent": "PeopleOps-Hosted-Provider-Evaluation/1.0"},
    ) as client:
        health_response = client.get("/health")
        health_response.raise_for_status()
        health = health_response.json()
        results = []
        for case in CASES:
            started = perf_counter()
            response = client.post(
                "/chat",
                json={
                    "message": case["prompt"],
                    "employee_id": case["employee_id"],
                },
            )
            duration_ms = max(0, round((perf_counter() - started) * 1000))
            response.raise_for_status()
            chat = ChatResponse.model_validate(response.json())
            tools = {item.tool_name for item in chat.tool_trace}
            sections = {item.section_id for item in chat.citations}
            failures = []
            if chat.workflow.value != case["workflow"]:
                failures.append(f"workflow={chat.workflow.value}, expected={case['workflow']}")
            if chat.outcome.value != case["outcome"]:
                failures.append(f"outcome={chat.outcome.value}, expected={case['outcome']}")
            if sections != case["sections"]:
                failures.append(
                    f"sections={sorted(sections)}, expected={sorted(case['sections'])}"
                )
            if not case["tools"] <= tools:
                failures.append(f"missing tools={sorted(case['tools'] - tools)}")
            if "create_mock_hr_ticket" in tools or chat.pending_action is not None:
                failures.append("read-only evaluation attempted a write action")
            results.append(
                {
                    "case_id": case["case_id"],
                    "duration_ms": duration_ms,
                    "workflow": chat.workflow.value,
                    "outcome": chat.outcome.value,
                    "generation": chat.generation.model_dump(mode="json"),
                    "sections": sorted(sections),
                    "tools": sorted(tools),
                    "workflow_integrity_pass": not failures,
                    "failures": failures,
                    "request_id": str(chat.request_id),
                    "trace_id": str(chat.trace_id),
                }
            )

    durations = [item["duration_ms"] for item in results]
    provider_accepts = sum(item["generation"]["mode"] == "provider" for item in results)
    workflow_passes = sum(item["workflow_integrity_pass"] for item in results)
    provider_component = health.get("components", {}).get("llm_provider", {})
    provider_ready = provider_component.get("status") == "ready"
    total = len(results)
    return {
        "phase": 10,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "base_url": base_url.rstrip("/"),
        "release_sha": health.get("release_sha"),
        "environment": health.get("environment"),
        "llm_provider_health": provider_component,
        "methodology": (
            "Three read-only production workflows measure accepted provider synthesis versus "
            "verified deterministic fallback while independently requiring exact workflow, "
            "citation, tool, and no-write-action integrity. Provider acceptance is an observed "
            "free-tier metric, not an SLA or a correctness dependency."
        ),
        "metrics": {
            "executed_cases": total,
            "provider_accepted": provider_accepts,
            "provider_acceptance_rate": round(provider_accepts / total, 4),
            "deterministic_fallback_rate": round((total - provider_accepts) / total, 4),
            "workflow_integrity_rate": round(workflow_passes / total, 4),
            "provider_health_ready": provider_ready,
            "end_to_end_latency_ms": {
                "p50": round(statistics.median(durations)),
                "p95": _p95(durations),
                "min": min(durations),
                "max": max(durations),
            },
        },
        "target_met": provider_ready and workflow_passes == total and total == 3,
        "cases": results,
    }


def check_committed() -> tuple[bool, str]:
    if not RESULT_PATH.is_file():
        return False, "hosted provider evidence is missing"
    payload = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    metrics = payload.get("metrics", {})
    checks = (
        metrics.get("executed_cases") == 3,
        metrics.get("workflow_integrity_rate") == 1.0,
        isinstance(metrics.get("provider_acceptance_rate"), (int, float)),
        metrics.get("provider_health_ready") is True,
        payload.get("target_met") is True,
        len(payload.get("cases", [])) == 3,
    )
    return all(checks), "hosted provider evidence is valid" if all(checks) else (
        "hosted provider evidence is missing required observations"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate hosted provider behavior.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    if arguments.check:
        passed, message = check_committed()
        print(message)
        return 0 if passed else 1
    result = evaluate(arguments.base_url, arguments.timeout_seconds)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if arguments.write:
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["target_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
