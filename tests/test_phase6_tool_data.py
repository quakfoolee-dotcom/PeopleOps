from datetime import date
from decimal import Decimal

import pytest

from peopleops_mcp.tools import (
    check_policy_compliance_data,
    check_pto_balance_data,
    draft_hr_email_data,
    get_policy_section_data,
    lookup_benefits_status_data,
)


def test_exact_policy_section_returns_only_authoritative_chunks() -> None:
    result = get_policy_section_data("POL-PTO-001", "PTO-6")

    assert result.found is True
    assert result.index_version == "phase5-hybrid-v2"
    assert {item.policy_id for item in result.evidence} == {"POL-PTO-001"}
    assert {item.section_id for item in result.evidence} == {"PTO-6"}
    assert all(item.retrieval_score == 1 for item in result.evidence)

    missing = get_policy_section_data("POL-PTO-001", "PTO-999")
    assert missing.found is False
    assert missing.evidence == []


def test_pto_balance_calculates_weekdays_and_never_mutates_balance() -> None:
    result = check_pto_balance_data(
        "E-1021",
        date(2026, 9, 21),
        date(2026, 9, 23),
    )

    assert result.found is True
    assert result.requested_workdays == 3
    assert result.requested_hours == Decimal("24.00")
    assert result.available_hours == Decimal("96.00")
    assert result.projected_hours_after_request == Decimal("72.00")
    assert result.sufficient_balance is True
    assert result.approval_required is True

    repeated = check_pto_balance_data(
        "E-1021",
        date(2026, 9, 21),
        date(2026, 9, 23),
    )
    assert repeated.available_hours == Decimal("96.00")


def test_pto_balance_fails_safely_for_unknown_employee_and_invalid_range() -> None:
    unknown = check_pto_balance_data(
        "E-9999",
        date(2026, 9, 21),
        date(2026, 9, 23),
    )
    assert unknown.found is False
    assert unknown.available_hours is None

    with pytest.raises(ValueError, match="request_end"):
        check_pto_balance_data(
            "E-1021",
            date(2026, 9, 23),
            date(2026, 9, 21),
        )


def test_benefits_lookup_returns_minimum_necessary_status() -> None:
    result = lookup_benefits_status_data("E-1003")

    assert result.found is True
    assert result.eligibility_status == "eligible"
    assert result.enrollment_status == "enrolled"
    assert result.plan_code == "PLAN-CORE-CA"
    assert result.coverage_tier == "family"
    assert result.minimum_necessary is True


def test_compliance_tool_covers_remote_pto_and_expense_rules() -> None:
    remote = check_policy_compliance_data(
        "international_remote_work",
        "E-1007",
        destination_country_code="DE",
        duration_business_days=30,
    )
    assert remote.status == "conditionally_eligible"
    assert remote.category == "international_exceptional"
    assert {"VP sponsor", "Legal"}.issubset(remote.required_approvals)
    assert remote.decision_is_approval is False

    unclassified_country = check_policy_compliance_data(
        "international_remote_work",
        "E-1007",
        destination_country_code="FR",
        duration_business_days=10,
    )
    assert unclassified_country.status == "needs_clarification"
    assert unclassified_country.category == "country_risk_unclassified"

    pto = check_policy_compliance_data(
        "pto_request",
        "E-1021",
        request_start=date(2026, 9, 21),
        request_end=date(2026, 9, 23),
    )
    assert pto.status == "conditionally_eligible"
    assert pto.calculation.business_days == 3
    assert pto.calculation.normal_notice_business_days == 10

    expense = check_policy_compliance_data(
        "home_office_expense",
        "E-1014",
        expense_amount=Decimal("900"),
        currency="CAD",
    )
    assert expense.status == "conditionally_eligible"
    assert expense.category == "ordinary_cap_partial"
    assert expense.calculation.ordinary_reimbursement_cap == Decimal("500")
    assert expense.calculation.employee_paid_remainder == Decimal("400")
    assert expense.required_approvals == ["Manager", "Director or designated budget owner"]

    generic_expense = check_policy_compliance_data(
        "home_office_expense",
        None,
        expense_amount=Decimal("900"),
        currency="CAD",
    )
    assert generic_expense.employee_id is None
    assert generic_expense.status == "conditionally_eligible"


def test_compliance_tool_requires_missing_inputs_and_known_employee() -> None:
    incomplete = check_policy_compliance_data(
        "international_remote_work",
        "E-1007",
    )
    assert incomplete.status == "needs_clarification"
    assert set(incomplete.clarification_needed) == {
        "destination country code",
        "expected business days worked",
    }

    unknown = check_policy_compliance_data(
        "pto_request",
        "E-9999",
        request_start=date(2026, 9, 21),
        request_end=date(2026, 9, 23),
    )
    assert unknown.status == "not_found"
    assert unknown.required_policy_sections == []


def test_email_tool_returns_a_non_persistent_draft() -> None:
    result = draft_hr_email_data(
        "pto_manager_request",
        "E-1021",
        request_start=date(2026, 9, 21),
        request_end=date(2026, 9, 23),
    )

    assert result.label == "Draft - not sent"
    assert result.recipient == "Kendall Price"
    assert result.sent is False
    assert result.persisted is False
    assert "2026-09-21" in result.body
    assert "approved HR system" in result.body
