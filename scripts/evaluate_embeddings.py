from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.rag.embeddings import LocalHashEmbedding, cosine_similarity  # noqa: E402
from app.rag.index import cached_index  # noqa: E402
from app.rag.retrieval import HybridRetriever  # noqa: E402

RESULT_PATH = PROJECT_ROOT / "evaluation" / "results" / "phase10_embedding_comparison.json"
NEURAL_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _cases() -> list[dict[str, Any]]:
    payload = json.loads(
        (PROJECT_ROOT / "evaluation" / "gold_cases.json").read_text(encoding="utf-8")
    )
    return [case for case in payload["cases"] if case["expected_policy_sections"]]


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round(quantile * len(ordered)) - 1))
    return round(ordered[index], 3)


def _summary(
    *,
    name: str,
    case_results: list[dict[str, Any]],
    latencies: list[float],
    index_seconds: float,
    dimensions: int,
) -> dict[str, Any]:
    expected = sum(item["expected_count"] for item in case_results)
    matched = sum(item["matched_count"] for item in case_results)
    return {
        "model": name,
        "dimensions": dimensions,
        "top_k": 5,
        "evaluated_cases": len(case_results),
        "expected_sections": expected,
        "retrieved_expected_sections": matched,
        "evidence_recall": round(matched / expected, 4),
        "index_build_seconds": round(index_seconds, 3),
        "query_latency_ms": {
            "p50": round(statistics.median(latencies), 3),
            "p95": _percentile(latencies, 0.95),
        },
        "case_results": case_results,
    }


def _evaluate_hash(index: Any, cases: list[dict[str, Any]]) -> dict[str, Any]:
    model = LocalHashEmbedding(index.embedding_dimensions)
    results = []
    latencies = []
    for case in cases:
        started = perf_counter()
        query = model.embed(case["prompt"])
        ranked = sorted(
            index.indexed_chunks,
            key=lambda item: cosine_similarity(query, item.embedding),
            reverse=True,
        )[:5]
        latencies.append((perf_counter() - started) * 1000)
        expected = {
            (item["policy_id"], item["section_id"])
            for item in case["expected_policy_sections"]
        }
        retrieved = {(item.chunk.policy_id, item.chunk.section_id) for item in ranked}
        results.append(
            {
                "case_id": case["case_id"],
                "expected_count": len(expected),
                "matched_count": len(expected & retrieved),
            }
        )
    return _summary(
        name=model.name,
        case_results=results,
        latencies=latencies,
        index_seconds=0.0,
        dimensions=index.embedding_dimensions,
    )


def _evaluate_neural(index: Any, cases: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise RuntimeError(
            "Install the neural evaluation extra: pip install -e '.[neural-eval]'"
        ) from error

    model = SentenceTransformer(NEURAL_MODEL)
    chunk_texts = [
        " ".join(
            (
                chunk.policy_title,
                chunk.section_title,
                chunk.applicability,
                chunk.text,
            )
        )
        for chunk in index.chunks
    ]
    started = perf_counter()
    chunk_vectors = model.encode(
        chunk_texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    index_seconds = perf_counter() - started
    results = []
    latencies = []
    for case in cases:
        started = perf_counter()
        query = model.encode(
            [case["prompt"]],
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0]
        scores = chunk_vectors @ query
        ranked_indices = scores.argsort()[-5:][::-1]
        latencies.append((perf_counter() - started) * 1000)
        expected = {
            (item["policy_id"], item["section_id"])
            for item in case["expected_policy_sections"]
        }
        retrieved = {
            (index.chunks[position].policy_id, index.chunks[position].section_id)
            for position in ranked_indices
        }
        results.append(
            {
                "case_id": case["case_id"],
                "expected_count": len(expected),
                "matched_count": len(expected & retrieved),
            }
        )
    dimensions = int(chunk_vectors.shape[1])
    return _summary(
        name=NEURAL_MODEL,
        case_results=results,
        latencies=latencies,
        index_seconds=index_seconds,
        dimensions=dimensions,
    )


def evaluate() -> dict[str, Any]:
    settings = get_settings()
    index = cached_index(
        settings.policy_corpus_directory.resolve(),
        settings.rag_index_path.resolve(),
        settings.rag_embedding_dimensions,
        settings.rag_chunk_target_words,
        settings.rag_chunk_overlap_words,
    )
    cases = _cases()
    hybrid = HybridRetriever(index)
    hybrid_recalled = 0
    expected_total = 0
    for case in cases:
        expected = {
            (item["policy_id"], item["section_id"])
            for item in case["expected_policy_sections"]
        }
        retrieved = {
            (hit.chunk.policy_id, hit.chunk.section_id)
            for hit in hybrid.search(case["prompt"], top_k=8, mode="hybrid").hits
        }
        expected_total += len(expected)
        hybrid_recalled += len(expected & retrieved)

    hash_result = _evaluate_hash(index, cases)
    neural_result = _evaluate_neural(index, cases)
    hybrid_recall = round(hybrid_recalled / expected_total, 4)
    return {
        "phase": 10,
        "suite": "Gold policy-evidence embedding comparison",
        "synthetic_as_of_date": settings.synthetic_as_of_date.isoformat(),
        "corpus_fingerprint": index.corpus_fingerprint,
        "methodology": (
            "The same 24 gold prompts, persisted policy chunks, top-k=5, and section-level "
            "micro-recall calculation are used for feature-hash and neural dense retrieval. "
            "The deployed hybrid-k8 recall is reported as the production selection baseline."
        ),
        "dense_comparison": {
            "feature_hash": hash_result,
            "neural": neural_result,
        },
        "production_selection": {
            "model": index.embedding_model,
            "mode": "hybrid",
            "top_k": 8,
            "evidence_recall": hybrid_recall,
            "decision": (
                "Retain the deterministic dependency-free hybrid-k8 configuration because it "
                "meets the 0.95 evidence-recall gate; the neural result is an evaluated option, "
                "not an unevaluated production claim."
            ),
        },
        "target_met": hybrid_recall >= 0.95,
    }


def check_committed() -> tuple[bool, str]:
    if not RESULT_PATH.is_file():
        return False, "embedding comparison evidence is missing"
    payload = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    settings = get_settings()
    index = cached_index(
        settings.policy_corpus_directory.resolve(),
        settings.rag_index_path.resolve(),
        settings.rag_embedding_dimensions,
        settings.rag_chunk_target_words,
        settings.rag_chunk_overlap_words,
    )
    checks = (
        payload.get("corpus_fingerprint") == index.corpus_fingerprint,
        payload.get("dense_comparison", {}).get("neural", {}).get("model") == NEURAL_MODEL,
        payload.get("dense_comparison", {}).get("neural", {}).get("evaluated_cases") == 24,
        payload.get("production_selection", {}).get("evidence_recall", 0) >= 0.95,
        payload.get("target_met") is True,
    )
    return all(checks), "embedding comparison evidence is current" if all(checks) else (
        "embedding comparison evidence is stale or incomplete"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare hash and neural dense embeddings.")
    parser.add_argument("--write", action="store_true", help="Write the evidence artifact.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate committed evidence without loading the neural model.",
    )
    arguments = parser.parse_args()
    if arguments.check:
        passed, message = check_committed()
        print(message)
        return 0 if passed else 1
    result = evaluate()
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if arguments.write:
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["target_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
