from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.evaluation.runner import evaluate_gold_suite  # noqa: E402

RESULTS_DIRECTORY = PROJECT_ROOT / "evaluation" / "results"
JSON_RESULT = RESULTS_DIRECTORY / "phase10_gold_evaluation.json"
CSV_RESULT = RESULTS_DIRECTORY / "phase10_gold_evaluation.csv"


def _write_csv(result: dict[str, object]) -> None:
    cases = result["cases"]
    assert isinstance(cases, list)
    with CSV_RESULT.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "case_id",
                "category",
                "expected_outcome",
                "actual_outcome",
                "workflow",
                "duration_ms",
                "groundedness_pass",
                "answer_fact_accuracy_pass",
                "answer_constraint_pass",
                "claim_citation_support_pass",
                "citation_accuracy_pass",
                "citation_coverage_pass",
                "tool_selection_pass",
                "workflow_completion_pass",
                "action_safety_pass",
                "tools",
                "returned_sections",
                "failures",
            ],
        )
        writer.writeheader()
        for item in cases:
            assert isinstance(item, dict)
            row = dict(item)
            for field in ("tools", "returned_sections", "failures"):
                row[field] = " | ".join(str(value) for value in row[field])
            writer.writerow({key: row[key] for key in writer.fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the complete Phase 10 gold evaluation.")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write committed JSON and CSV results.",
    )
    parser.add_argument("--reliability-repeats", type=int, default=10)
    parser.add_argument("--latency-sample-count", type=int, default=20)
    arguments = parser.parse_args()
    result = asyncio.run(
        evaluate_gold_suite(
            reliability_repeats=arguments.reliability_repeats,
            latency_sample_count=arguments.latency_sample_count,
        )
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if arguments.write:
        RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
        JSON_RESULT.write_text(rendered, encoding="utf-8")
        _write_csv(result)
    print(rendered, end="")
    return 0 if result["score5_targets_met"] and result["all_25_cases_executed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
