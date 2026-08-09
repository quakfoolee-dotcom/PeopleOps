from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from app.api.contracts import Citation, DecisionSummary, WorkflowKind


@dataclass(frozen=True, slots=True)
class GroundedSynthesisRequest:
    request_id: str
    user_message: str
    workflow: WorkflowKind
    deterministic_answer: str
    decision_summary: DecisionSummary
    citations: tuple[Citation, ...]
    protected_facts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GroundedSynthesisResult:
    summary: str
    provider: str
    configured_model: str
    resolved_model: str
    duration_ms: int
    cited_chunk_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    status: Literal["ready", "not_configured", "error"]
    detail: str


class LLMProvider(Protocol):
    name: str
    model: str
    configured: bool

    async def synthesize(
        self, request: GroundedSynthesisRequest
    ) -> GroundedSynthesisResult: ...

    async def health(self) -> ProviderHealth: ...
