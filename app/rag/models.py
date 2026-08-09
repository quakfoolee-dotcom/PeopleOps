from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Literal

SourceFormat = Literal["markdown", "pdf"]


@dataclass(frozen=True, slots=True)
class PolicyChunk:
    chunk_id: str
    policy_id: str
    policy_title: str
    section_id: str
    section_title: str
    text: str
    version: str
    effective_date: date
    owner: str
    applicability: str
    source_format: SourceFormat
    source_path: str
    page: int | None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["effective_date"] = self.effective_date.isoformat()
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> PolicyChunk:
        payload = dict(value)
        payload["effective_date"] = date.fromisoformat(str(payload["effective_date"]))
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class IndexedChunk:
    chunk: PolicyChunk
    embedding: tuple[float, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"chunk": self.chunk.to_dict(), "embedding": list(self.embedding)}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> IndexedChunk:
        return cls(
            chunk=PolicyChunk.from_dict(value["chunk"]),
            embedding=tuple(float(item) for item in value["embedding"]),
        )


@dataclass(frozen=True, slots=True)
class SearchHit:
    chunk: PolicyChunk
    score: float
    keyword_score: float
    embedding_score: float
    matched_facets: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class QueryPlan:
    query: str
    facets: tuple[str, ...]
    required_policy_ids: frozenset[str]
    evidence_rule: str


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    query: str
    mode: str
    hits: tuple[SearchHit, ...]
    sufficient_evidence: bool
    evidence_rule: str
    missing_policy_ids: tuple[str, ...]
    conflicts: tuple[str, ...]
    limitation: str
