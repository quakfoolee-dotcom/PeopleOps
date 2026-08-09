from __future__ import annotations

import re
from collections.abc import Iterable

from app.rag.index import HybridIndex
from app.rag.models import SearchHit


class CitationValidationError(ValueError):
    pass


def citation_snippet(text: str, *, max_length: int = 1000) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3].rstrip() + "..."


def validate_retrieved_hits(index: HybridIndex, hits: Iterable[SearchHit]) -> None:
    authoritative = {item.chunk.chunk_id: item.chunk for item in index.indexed_chunks}
    seen: set[str] = set()
    for hit in hits:
        chunk = hit.chunk
        if chunk.chunk_id in seen:
            raise CitationValidationError(f"duplicate citation chunk: {chunk.chunk_id}")
        seen.add(chunk.chunk_id)
        source = authoritative.get(chunk.chunk_id)
        if source is None:
            raise CitationValidationError(
                f"citation is not in the retrieved index: {chunk.chunk_id}"
            )
        if (
            source.policy_id != chunk.policy_id
            or source.section_id != chunk.section_id
            or source.source_path != chunk.source_path
            or source.text != chunk.text
        ):
            raise CitationValidationError(
                f"citation metadata does not match the authoritative index: {chunk.chunk_id}"
            )
