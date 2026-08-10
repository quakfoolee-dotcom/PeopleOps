import json
import re
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from app.core.config import PROJECT_ROOT
from app.core.constants import SYNTHETIC_AS_OF_DATE
from app.evaluation.answer_quality import (
    load_answer_check_suite,
    validate_answer_check_suite,
)
from app.evaluation.contracts import EvaluationCategory, GoldEvaluationSuite
from peopleops_mcp.contracts import REQUIRED_TOOL_CONTRACTS

GOLD_SUITE_PATH = PROJECT_ROOT / "evaluation" / "gold_cases.json"
POLICY_SOURCE_DIRECTORY = PROJECT_ROOT / "policy_corpus" / "master_markdown"

EXPECTED_CATEGORY_COUNTS = {
    EvaluationCategory.STRAIGHTFORWARD_POLICY: 7,
    EvaluationCategory.MULTI_DOCUMENT_POLICY: 5,
    EvaluationCategory.EMPLOYEE_TOOL_WORKFLOW: 6,
    EvaluationCategory.AMBIGUOUS_CLARIFICATION: 4,
    EvaluationCategory.OUT_OF_SCOPE_SAFETY: 3,
}

SECTION_PATTERN = re.compile(r"^## (?P<section>[A-Z]{3}-\d+(?:\.\d+)?)\.", re.MULTILINE)
POLICY_PATTERN = re.compile(r"POL-[A-Z]{3}-\d{3}")


def load_gold_suite(path: Path = GOLD_SUITE_PATH) -> GoldEvaluationSuite:
    with path.open(encoding="utf-8") as suite_file:
        payload = json.load(suite_file)
    return GoldEvaluationSuite.model_validate(payload)


def load_policy_section_catalog(
    source_directory: Path = POLICY_SOURCE_DIRECTORY,
) -> set[tuple[str, str]]:
    catalog: set[tuple[str, str]] = set()
    for source_path in source_directory.glob("*.md"):
        policy_match = POLICY_PATTERN.search(source_path.name)
        if policy_match is None:
            continue
        policy_id = policy_match.group(0)
        text = source_path.read_text(encoding="utf-8")
        catalog.update(
            (policy_id, match.group("section")) for match in SECTION_PATTERN.finditer(text)
        )
    return catalog


def validate_gold_suite(suite: GoldEvaluationSuite) -> list[str]:
    errors: list[str] = []
    category_counts = Counter(case.category for case in suite.cases)
    if category_counts != Counter(EXPECTED_CATEGORY_COUNTS):
        errors.append(
            f"category distribution is {dict(category_counts)}, expected {EXPECTED_CATEGORY_COUNTS}"
        )

    if suite.as_of_date != SYNTHETIC_AS_OF_DATE:
        errors.append(
            f"as-of date is {suite.as_of_date}, expected {SYNTHETIC_AS_OF_DATE}"
        )

    known_sections = load_policy_section_catalog()
    known_tools = {contract.name for contract in REQUIRED_TOOL_CONTRACTS}
    errors.extend(
        validate_answer_check_suite(
            suite,
            load_answer_check_suite(),
            known_sections=known_sections,
            known_tools=known_tools,
        )
    )

    for case in suite.cases:
        for section in case.expected_policy_sections:
            key = (section.policy_id, section.section_id)
            if key not in known_sections:
                errors.append(f"{case.case_id} references unknown policy section {key}")

        declared_tools = set(
            case.tools.required + case.tools.forbidden + case.tools.after_confirmation
        )
        if unknown_tools := declared_tools - known_tools:
            errors.append(f"{case.case_id} references unknown tools {sorted(unknown_tools)}")

        referenced_policies = {
            section.policy_id for section in case.expected_policy_sections
        }
        if (
            case.category is EvaluationCategory.MULTI_DOCUMENT_POLICY
            and len(referenced_policies) < 2
        ):
            errors.append(f"{case.case_id} must reference at least two policies")

        if case.category is EvaluationCategory.EMPLOYEE_TOOL_WORKFLOW and case.employee_id is None:
            errors.append(f"{case.case_id} must identify a synthetic employee")

        if "create_mock_hr_ticket" in case.tools.required:
            errors.append(
                f"{case.case_id} cannot require create_mock_hr_ticket before confirmation"
            )

    return errors


def validate_gold_suite_file(path: Path = GOLD_SUITE_PATH) -> list[str]:
    try:
        suite = load_gold_suite(path)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        return [f"gold suite cannot be loaded: {error}"]
    return validate_gold_suite(suite)
