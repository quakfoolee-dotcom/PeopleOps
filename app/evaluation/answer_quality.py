from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.api.contracts import ChatResponse
from app.evaluation.contracts import (
    AnswerCheck,
    AnswerCheckSuite,
    CaseAnswerChecks,
    GoldEvaluationCase,
    GoldEvaluationSuite,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ANSWER_CHECKS_PATH = PROJECT_ROOT / "evaluation" / "answer_checks.json"
WORD_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*", re.IGNORECASE)
NUMBER_PATTERN = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?")
STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "before",
        "but",
        "by",
        "can",
        "for",
        "from",
        "in",
        "is",
        "it",
        "must",
        "of",
        "on",
        "or",
        "should",
        "that",
        "the",
        "their",
        "this",
        "through",
        "to",
        "until",
        "when",
        "while",
        "with",
    }
)


def _normalized(value: str) -> str:
    return " ".join(WORD_PATTERN.findall(value.casefold()))


def _authoritative_answer(answer: str) -> str:
    marker = "Verified workflow result\n"
    return answer.split(marker, maxsplit=1)[-1].strip() if marker in answer else answer.strip()


def _stem(value: str) -> str:
    if len(value) > 5 and value.endswith("ing"):
        return value[:-3]
    if len(value) > 4 and value.endswith("ed"):
        return value[:-2]
    if len(value) > 4 and value.endswith("s") and not value.endswith("ss"):
        return value[:-1]
    return value


def _content_tokens(value: str) -> set[str]:
    return {
        _stem(token)
        for token in WORD_PATTERN.findall(value.casefold())
        if token not in STOP_WORDS and len(token) > 2
    }


@lru_cache
def load_answer_check_suite(path: Path = ANSWER_CHECKS_PATH) -> AnswerCheckSuite:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return AnswerCheckSuite.model_validate(payload)


def validate_answer_check_suite(
    gold_suite: GoldEvaluationSuite,
    check_suite: AnswerCheckSuite,
    *,
    known_sections: set[tuple[str, str]],
    known_tools: set[str],
) -> list[str]:
    errors: list[str] = []
    gold_by_id = {case.case_id: case for case in gold_suite.cases}
    checks_by_id = {case.case_id: case for case in check_suite.cases}
    if set(gold_by_id) != set(checks_by_id):
        missing = sorted(set(gold_by_id) - set(checks_by_id))
        unexpected = sorted(set(checks_by_id) - set(gold_by_id))
        errors.append(
            f"answer-check case coverage differs: missing={missing}, unexpected={unexpected}"
        )

    for case_id, gold_case in gold_by_id.items():
        checks = checks_by_id.get(case_id)
        if checks is None:
            continue
        if len(checks.fact_checks) != len(gold_case.expected_facts):
            errors.append(
                f"{case_id} has {len(checks.fact_checks)} fact checks for "
                f"{len(gold_case.expected_facts)} expected facts"
            )
        if len(checks.constraint_checks) != len(gold_case.answer_constraints):
            errors.append(
                f"{case_id} has {len(checks.constraint_checks)} constraint checks for "
                f"{len(gold_case.answer_constraints)} answer constraints"
            )
        for check in checks.fact_checks + checks.constraint_checks:
            for section in check.supporting_sections:
                key = (section.policy_id, section.section_id)
                if key not in known_sections:
                    errors.append(f"{case_id} answer check references unknown section {key}")
            unknown_tools = set(check.supporting_tools) - known_tools
            if unknown_tools:
                errors.append(
                    f"{case_id} answer check references unknown tools {sorted(unknown_tools)}"
                )
            if check.mode in {"tools_present", "tools_absent"}:
                unknown_values = set(check.values) - known_tools
                if unknown_values:
                    errors.append(
                        f"{case_id} answer check references unknown tool values "
                        f"{sorted(unknown_values)}"
                    )
            if check.mode == "pending_action" and set(check.values) - {"present", "absent"}:
                errors.append(f"{case_id} pending-action checks accept only present or absent")
    return errors


def _evaluate_check(
    check: AnswerCheck,
    *,
    answer: str,
    response: ChatResponse,
    actual_tools: set[str],
) -> tuple[bool, str]:
    normalized_answer = _normalized(answer)
    normalized_values = [_normalized(value) for value in check.values]
    if check.mode == "contains_all":
        missing = [
            original
            for original, normalized in zip(check.values, normalized_values, strict=True)
            if normalized not in normalized_answer
        ]
        return not missing, f"missing answer fragments: {missing}" if missing else "matched all"
    if check.mode == "contains_any":
        matched = any(value in normalized_answer for value in normalized_values)
        return matched, "matched one" if matched else f"matched none of {check.values}"
    if check.mode == "contains_none":
        present = [
            original
            for original, normalized in zip(check.values, normalized_values, strict=True)
            if normalized in normalized_answer
        ]
        detail = f"forbidden answer fragments present: {present}" if present else "absent"
        return not present, detail
    if check.mode == "starts_with_any":
        matched = any(normalized_answer.startswith(value) for value in normalized_values)
        detail = "matched prefix" if matched else f"unexpected answer prefix: {answer[:80]!r}"
        return matched, detail
    if check.mode == "citation_sections":
        returned = {f"{item.policy_id}:{item.section_id}" for item in response.citations}
        expected = set(check.values)
        missing = sorted(expected - returned)
        return not missing, f"missing citation sections: {missing}" if missing else "present"
    if check.mode == "tools_present":
        missing = sorted(set(check.values) - actual_tools)
        return not missing, f"missing tools: {missing}" if missing else "present"
    if check.mode == "tools_absent":
        present = sorted(set(check.values) & actual_tools)
        return not present, f"unexpected tools: {present}" if present else "absent"
    if check.mode == "pending_action":
        expected_present = check.values == ["present"]
        matched = (response.pending_action is not None) is expected_present
        return matched, "matched" if matched else "pending-action state differed"
    if check.mode == "outcome":
        matched = response.outcome.value in check.values
        return matched, "matched" if matched else f"outcome was {response.outcome.value}"
    raise ValueError(f"unsupported answer-check mode: {check.mode}")


def _support_result(
    expected_fact: str,
    check: AnswerCheck,
    *,
    response: ChatResponse,
    actual_tools: set[str],
) -> tuple[bool, dict[str, Any]]:
    required_sections = {
        (section.policy_id, section.section_id) for section in check.supporting_sections
    }
    citations = {
        (citation.policy_id, citation.section_id): citation for citation in response.citations
    }
    missing_sections = sorted(required_sections - set(citations))
    missing_tools = sorted(set(check.supporting_tools) - actual_tools)
    lexical_score = 1.0
    lexical_threshold = 0.0
    missing_numbers: list[str] = []
    if required_sections and not missing_sections:
        evidence_text = " ".join(citations[key].snippet for key in required_sections)
        fact_tokens = _content_tokens(expected_fact)
        evidence_tokens = _content_tokens(evidence_text)
        overlap = len(fact_tokens & evidence_tokens)
        lexical_score = overlap / len(fact_tokens) if fact_tokens else 1.0
        lexical_threshold = min(0.45, max(0.25, 2 / max(len(fact_tokens), 1)))
        expected_numbers = set(NUMBER_PATTERN.findall(expected_fact))
        evidence_numbers = set(NUMBER_PATTERN.findall(evidence_text))
        missing_numbers = sorted(expected_numbers - evidence_numbers)
    passed = bool(
        not missing_sections
        and not missing_tools
        and lexical_score >= lexical_threshold
        and not missing_numbers
    )
    return passed, {
        "supporting_sections": [
            f"{policy}:{section}" for policy, section in sorted(required_sections)
        ],
        "supporting_tools": sorted(check.supporting_tools),
        "missing_sections": [f"{policy}:{section}" for policy, section in missing_sections],
        "missing_tools": missing_tools,
        "lexical_support": round(lexical_score, 4),
        "lexical_threshold": round(lexical_threshold, 4),
        "missing_numbers": missing_numbers,
    }


def evaluate_answer_quality(
    case: GoldEvaluationCase,
    checks: CaseAnswerChecks,
    response: ChatResponse,
    actual_tools: set[str],
) -> dict[str, Any]:
    answer = _authoritative_answer(response.answer)
    fact_results = []
    for expected_fact, check in zip(case.expected_facts, checks.fact_checks, strict=True):
        content_pass, detail = _evaluate_check(
            check,
            answer=answer,
            response=response,
            actual_tools=actual_tools,
        )
        support_pass, support = _support_result(
            expected_fact,
            check,
            response=response,
            actual_tools=actual_tools,
        )
        fact_results.append(
            {
                "expected_fact": expected_fact,
                "content_pass": content_pass,
                "support_pass": support_pass,
                "passed": content_pass and support_pass,
                "detail": detail,
                "support": support,
            }
        )

    constraint_results = []
    for description, check in zip(
        case.answer_constraints,
        checks.constraint_checks,
        strict=True,
    ):
        passed, detail = _evaluate_check(
            check,
            answer=answer,
            response=response,
            actual_tools=actual_tools,
        )
        constraint_results.append(
            {"constraint": description, "passed": passed, "detail": detail}
        )

    fact_accuracy = all(item["content_pass"] for item in fact_results)
    constraint_adherence = all(item["passed"] for item in constraint_results)
    claim_citation_support = all(item["support_pass"] for item in fact_results)
    return {
        "authoritative_answer": answer,
        "fact_results": fact_results,
        "constraint_results": constraint_results,
        "answer_fact_accuracy_pass": fact_accuracy,
        "answer_constraint_pass": constraint_adherence,
        "claim_citation_support_pass": claim_citation_support,
        "passed": fact_accuracy and constraint_adherence and claim_citation_support,
    }
