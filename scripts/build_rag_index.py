from __future__ import annotations

import argparse
import json
import sys

from app.core.config import get_settings
from app.rag.index import build_index, load_index, write_index


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify the Phase 5 RAG index.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed index matches the authoritative corpus.",
    )
    arguments = parser.parse_args()
    settings = get_settings()
    expected = build_index(
        settings.policy_corpus_directory,
        embedding_dimensions=settings.rag_embedding_dimensions,
        target_words=settings.rag_chunk_target_words,
        overlap_words=settings.rag_chunk_overlap_words,
    )

    if arguments.check:
        if not settings.rag_index_path.is_file():
            print(f"RAG index is missing: {settings.rag_index_path}", file=sys.stderr)
            return 1
        actual = load_index(settings.rag_index_path)
        if actual.to_dict() != expected.to_dict():
            print("Committed RAG index is stale; run scripts/build_rag_index.py", file=sys.stderr)
            return 1
        print(
            f"RAG index verified: {actual.policy_count} policies, "
            f"{actual.section_count} sections, {len(actual.indexed_chunks)} chunks."
        )
        return 0

    write_index(expected, settings.rag_index_path)
    summary = {
        "index_path": str(settings.rag_index_path),
        "index_version": expected.index_version,
        "embedding_model": expected.embedding_model,
        "policy_count": expected.policy_count,
        "section_count": expected.section_count,
        "chunk_count": len(expected.indexed_chunks),
        "source_format_counts": expected.source_format_counts,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
