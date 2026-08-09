from __future__ import annotations

import argparse
import csv
import json
import statistics
from time import perf_counter
from typing import Any

from app.core.config import PROJECT_ROOT, get_settings
from app.rag.index import cached_index
from app.rag.retrieval import HybridRetriever

RESULTS_DIRECTORY = PROJECT_ROOT / "evaluation" / "results"


def _load_cases() -> list[dict[str, Any]]:
    suite = json.loads((PROJECT_ROOT / "evaluation" / "gold_cases.json").read_text("utf-8"))
    return [case for case in suite["cases"] if case["expected_policy_sections"]]


def evaluate(mode: str, top_k: int) -> dict[str, Any]:
    settings = get_settings()
    index = cached_index(
        settings.policy_corpus_directory.resolve(),
        settings.rag_index_path.resolve(),
        settings.rag_embedding_dimensions,
        settings.rag_chunk_target_words,
        settings.rag_chunk_overlap_words,
    )
    retriever = HybridRetriever(index)
    cases = _load_cases()
    expected_total = 0
    retrieved_total = 0
    latencies = []
    case_results = []
    for case in cases:
        expected = {
            (item["policy_id"], item["section_id"])
            for item in case["expected_policy_sections"]
        }
        started = perf_counter()
        result = retriever.search(case["prompt"], top_k=top_k, mode=mode)
        latencies.append((perf_counter() - started) * 1000)
        retrieved = {(hit.chunk.policy_id, hit.chunk.section_id) for hit in result.hits}
        matched = expected & retrieved
        expected_total += len(expected)
        retrieved_total += len(matched)
        case_results.append(
            {
                "case_id": case["case_id"],
                "expected": sorted(f"{policy}:{section}" for policy, section in expected),
                "retrieved": sorted(f"{policy}:{section}" for policy, section in retrieved),
                "recall": round(len(matched) / len(expected), 4),
                "sufficient_evidence": result.sufficient_evidence,
            }
        )
    sorted_latency = sorted(latencies)
    p95_index = max(0, min(len(sorted_latency) - 1, round(0.95 * len(sorted_latency)) - 1))
    return {
        "mode": mode,
        "top_k": top_k,
        "evaluated_cases": len(cases),
        "expected_sections": expected_total,
        "retrieved_expected_sections": retrieved_total,
        "evidence_recall": round(retrieved_total / expected_total, 4),
        "latency_ms": {
            "p50": round(statistics.median(sorted_latency), 3),
            "p95": round(sorted_latency[p95_index], 3),
        },
        "case_results": case_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the deterministic Phase 5 RAG ablation.")
    parser.add_argument("--write", action="store_true", help="Write committed result artifacts.")
    arguments = parser.parse_args()
    configurations = (("dense", 5), ("hybrid", 5), ("hybrid", 8))
    results = [evaluate(mode, top_k) for mode, top_k in configurations]
    summary = {
        "suite": "phase5-rag-ablation",
        "synthetic_as_of_date": get_settings().synthetic_as_of_date.isoformat(),
        "configurations": results,
        "selected_configuration": "hybrid-k8",
    }
    print(json.dumps(summary, indent=2))
    if arguments.write:
        RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
        (RESULTS_DIRECTORY / "phase5_rag_ablation.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8"
        )
        with (RESULTS_DIRECTORY / "phase5_rag_ablation.csv").open(
            "w", newline="", encoding="utf-8"
        ) as output:
            writer = csv.DictWriter(
                output,
                fieldnames=(
                    "mode",
                    "top_k",
                    "evaluated_cases",
                    "expected_sections",
                    "retrieved_expected_sections",
                    "evidence_recall",
                    "latency_p50_ms",
                    "latency_p95_ms",
                ),
            )
            writer.writeheader()
            for result in results:
                writer.writerow(
                    {
                        **{key: result[key] for key in writer.fieldnames if key in result},
                        "latency_p50_ms": result["latency_ms"]["p50"],
                        "latency_p95_ms": result["latency_ms"]["p95"],
                    }
                )
    selected = next(
        result for result in results if result["mode"] == "hybrid" and result["top_k"] == 8
    )
    return 0 if selected["evidence_recall"] >= 0.95 else 1


if __name__ == "__main__":
    raise SystemExit(main())
