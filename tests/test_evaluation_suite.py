from collections import Counter
from datetime import date

from app.api.contracts import WorkflowOutcome
from app.evaluation.contracts import EvaluationCategory, PolicySectionTarget
from app.evaluation.gold import (
    EXPECTED_CATEGORY_COUNTS,
    load_gold_suite,
    validate_gold_suite,
    validate_gold_suite_file,
)


def test_gold_suite_meets_phase_two_exit_criterion() -> None:
    suite = load_gold_suite()

    assert suite.synthetic_only is True
    assert suite.as_of_date == date(2026, 8, 17)
    assert len(suite.cases) == 25
    assert Counter(case.category for case in suite.cases) == Counter(EXPECTED_CATEGORY_COUNTS)
    assert validate_gold_suite(suite) == []
    assert validate_gold_suite_file() == []


def test_every_case_defines_facts_tools_outcome_and_safety() -> None:
    suite = load_gold_suite()

    for case in suite.cases:
        assert case.expected_facts
        assert case.answer_constraints
        assert case.safety_behavior
        assert case.expected_outcome in WorkflowOutcome
        declared_tools = case.tools.required + case.tools.forbidden + case.tools.after_confirmation
        assert len(declared_tools) == len(set(declared_tools))


def test_multi_document_and_employee_cases_have_required_context() -> None:
    suite = load_gold_suite()

    for case in suite.cases:
        policy_ids = {section.policy_id for section in case.expected_policy_sections}
        if case.category is EvaluationCategory.MULTI_DOCUMENT_POLICY:
            assert len(policy_ids) >= 2
        if case.category is EvaluationCategory.EMPLOYEE_TOOL_WORKFLOW:
            assert case.employee_id is not None


def test_semantic_validator_reports_contract_drift() -> None:
    suite = load_gold_suite().model_copy(deep=True)
    suite.as_of_date = date(2026, 8, 18)
    suite.cases[0].category = EvaluationCategory.MULTI_DOCUMENT_POLICY
    suite.cases[0].expected_policy_sections = [
        PolicySectionTarget(policy_id="POL-PTO-001", section_id="PTO-999")
    ]
    suite.cases[0].tools.required.append("unknown_tool")
    suite.cases[12].employee_id = None
    suite.cases[13].tools.required.append("create_mock_hr_ticket")

    errors = validate_gold_suite(suite)

    assert any("category distribution" in error for error in errors)
    assert any("as-of date" in error for error in errors)
    assert any("unknown policy section" in error for error in errors)
    assert any("unknown tools" in error for error in errors)
    assert any("at least two policies" in error for error in errors)
    assert any("identify a synthetic employee" in error for error in errors)
    assert any("before confirmation" in error for error in errors)
