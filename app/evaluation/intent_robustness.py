from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.agent.workflows import classify_request
from app.evaluation.contracts import IntentRobustnessSuite

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTENT_CASES_PATH = PROJECT_ROOT / "evaluation" / "intent_cases.json"


def load_intent_suite(path: Path = INTENT_CASES_PATH) -> IntentRobustnessSuite:
    return IntentRobustnessSuite.model_validate_json(path.read_text(encoding="utf-8"))


def evaluate_intent_robustness() -> dict[str, Any]:
    suite = load_intent_suite()
    results = []
    for case in suite.cases:
        intent = classify_request(case.prompt, case.supplied_employee_id)
        actual = intent.model_dump(mode="json")
        failures = []
        if actual["kind"] != case.expected_kind.value:
            failures.append(
                f"kind={actual['kind']}, expected={case.expected_kind.value}"
            )
        for field, expected in case.expected_fields.items():
            value = actual.get(field)
            if value != expected:
                failures.append(f"{field}={value!r}, expected={expected!r}")
        clarification = actual.get("clarification_needed", [])
        for expected in case.clarification_contains:
            if expected not in clarification:
                failures.append(f"missing clarification={expected!r}")
        results.append(
            {
                "case_id": case.case_id,
                "title": case.title,
                "tags": case.tags,
                "expected_kind": case.expected_kind.value,
                "actual_kind": actual["kind"],
                "passed": not failures,
                "failures": failures,
                "actual_fields": {
                    field: actual.get(field) for field in case.expected_fields
                },
                "clarification_needed": clarification,
            }
        )

    passed = sum(item["passed"] for item in results)
    total = len(results)
    accuracy = round(passed / total, 4)
    return {
        "phase": 10,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "suite": "Intent paraphrase, typo, mixed-intent, and safety robustness",
        "methodology": (
            "Versioned prompts exercise routing aliases, common typos, entity extraction, "
            "mixed-intent clarification, adversarial confirmation bypass, and unsupported scope."
        ),
        "target": 1.0,
        "metrics": {
            "executed_cases": total,
            "passed_cases": passed,
            "routing_and_extraction_accuracy": accuracy,
        },
        "target_met": accuracy == 1.0 and total == 15,
        "error_analysis": [item for item in results if not item["passed"]],
        "cases": results,
    }
