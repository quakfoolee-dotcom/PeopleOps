from __future__ import annotations

import json
import re
from typing import Any

from app.providers.contracts import GroundedSynthesisRequest

FENCE_PATTERN = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
NUMBER_PATTERN = re.compile(r"(?<![A-Za-z])(?:CAD\s+)?\$?\d+(?:[.,]\d+)*(?:%|\b)")
EMPLOYEE_PATTERN = re.compile(r"\bE-\d{4}\b")
POLICY_PATTERN = re.compile(r"\bPOL-[A-Z]{3}-\d{3}\b")
SECTION_PATTERN = re.compile(r"\b[A-Z]{3}-\d+(?:\.\d+)?\b")


class ProviderResponseError(RuntimeError):
    """Raised when a provider response cannot pass the grounded-output gate."""


def citation_marker(chunk_id: str) -> str:
    policy_id, section_id, _ = chunk_id.split("::", maxsplit=2)
    return f"[{policy_id} § {section_id}]"


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def _content(payload: dict[str, Any]) -> tuple[str, list[str]]:
    summary = payload.get("summary")
    citation_ids = payload.get("citation_ids")
    if not isinstance(summary, str):
        raise ProviderResponseError("provider JSON must contain a string summary")
    if not isinstance(citation_ids, list) or not all(
        isinstance(item, str) for item in citation_ids
    ):
        raise ProviderResponseError("provider JSON must contain a string citation_ids list")
    return summary.strip(), citation_ids


def parse_and_validate_grounded_output(
    raw_content: str,
    request: GroundedSynthesisRequest,
) -> tuple[str, tuple[str, ...]]:
    rendered = FENCE_PATTERN.sub("", raw_content.strip())
    try:
        payload = json.loads(rendered)
    except json.JSONDecodeError as error:
        raise ProviderResponseError("provider returned invalid JSON") from error
    if not isinstance(payload, dict):
        raise ProviderResponseError("provider JSON must be an object")

    summary, citation_ids = _content(payload)
    if not 20 <= len(summary) <= 1800:
        raise ProviderResponseError("provider summary length is outside the safe range")

    allowed_ids = {citation.chunk_id for citation in request.citations}
    returned_ids = set(citation_ids)
    if returned_ids != allowed_ids or len(citation_ids) != len(returned_ids):
        raise ProviderResponseError("provider citations must exactly match verified evidence")
    for chunk_id in citation_ids:
        marker = citation_marker(chunk_id)
        if marker not in summary:
            raise ProviderResponseError(f"provider summary is missing marker {marker}")

    normalized_summary = _normalized(summary)
    for fact in request.protected_facts:
        if _normalized(fact) not in normalized_summary:
            raise ProviderResponseError(f"provider summary omitted protected fact: {fact}")

    allowed_text = " ".join(
        [
            request.deterministic_answer,
            request.decision_summary.model_dump_json(),
            *(citation.snippet for citation in request.citations),
            *(citation.policy_id for citation in request.citations),
            *(citation.section_id for citation in request.citations),
        ]
    )
    for pattern, label in (
        (NUMBER_PATTERN, "number"),
        (EMPLOYEE_PATTERN, "employee identifier"),
        (POLICY_PATTERN, "policy identifier"),
        (SECTION_PATTERN, "section identifier"),
    ):
        allowed = {_normalized(value) for value in pattern.findall(allowed_text)}
        introduced = {
            value for value in pattern.findall(summary) if _normalized(value) not in allowed
        }
        if introduced:
            raise ProviderResponseError(
                f"provider summary introduced an unverified {label}: {sorted(introduced)[0]}"
            )

    return summary, tuple(citation_ids)
