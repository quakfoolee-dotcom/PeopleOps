from __future__ import annotations

import hashlib
from datetime import date, timedelta
from decimal import Decimal
from functools import lru_cache

from app.core.config import get_settings
from app.data.store import load_seed_bundle
from app.rag.citations import citation_snippet, validate_retrieved_hits
from app.rag.index import cached_index
from app.rag.models import PolicyChunk
from app.rag.retrieval import HybridRetriever
from peopleops_mcp.actions import mock_ticket_actions
from peopleops_mcp.schemas import (
    BenefitsStatusResult,
    ComplianceCalculation,
    ComplianceCheckResult,
    EmployeeLocation,
    EmployeeProfile,
    EmployeeProfileResult,
    HREmailDraftResult,
    MockTicketActionResult,
    PolicyEvidence,
    PolicySearchResult,
    PolicySectionReference,
    PolicySectionResult,
    PTOBalanceResult,
)


@lru_cache(maxsize=1)
def _retriever() -> HybridRetriever:
    settings = get_settings()
    index = cached_index(
        settings.policy_corpus_directory.resolve(),
        settings.rag_index_path.resolve(),
        settings.rag_embedding_dimensions,
        settings.rag_chunk_target_words,
        settings.rag_chunk_overlap_words,
    )
    return HybridRetriever(index)


def clear_rag_caches() -> None:
    _retriever.cache_clear()
    cached_index.cache_clear()


def _policy_evidence(chunk: PolicyChunk, *, score: float) -> PolicyEvidence:
    return PolicyEvidence(
        policy_id=chunk.policy_id,
        section_id=chunk.section_id,
        title=f"{chunk.policy_title} - {chunk.section_title}",
        snippet=citation_snippet(chunk.text),
        version=chunk.version,
        effective_date=chunk.effective_date,
        source_format=chunk.source_format,
        source_path=chunk.source_path,
        page=chunk.page,
        chunk_id=chunk.chunk_id,
        retrieval_score=score,
    )


def _business_days(start: date, end: date) -> int:
    if end < start:
        raise ValueError("request_end must be on or after request_start")
    if (end - start).days > 366:
        raise ValueError("requested date range cannot exceed 366 calendar days")
    return sum(
        1
        for offset in range((end - start).days + 1)
        if (start + timedelta(days=offset)).weekday() < 5
    )


def lookup_employee_profile_data(employee_id: str) -> EmployeeProfileResult:
    bundle = load_seed_bundle()
    employee = next((item for item in bundle.employees if item.employee_id == employee_id), None)
    if employee is None:
        return EmployeeProfileResult(
            employee_id=employee_id,
            as_of_date=bundle.manifest.as_of_date,
            found=False,
        )

    location = next(
        item for item in bundle.locations if item.location_id == employee.home_office_id
    )
    return EmployeeProfileResult(
        employee_id=employee_id,
        as_of_date=bundle.manifest.as_of_date,
        found=True,
        profile=EmployeeProfile(
            employee_id=employee.employee_id,
            synthetic_name=employee.synthetic_name,
            employment_type=employee.employment_type.value,
            role=employee.role,
            department=employee.department,
            manager_id=employee.manager_id,
            remote_work_classification=employee.remote_work_classification.value,
            employment_status=employee.status.value,
            hire_date=employee.hire_date,
            home_office=EmployeeLocation(
                location_id=location.location_id,
                name=location.name,
                city=location.city,
                province_or_state=location.province_or_state,
                country_code=location.country_code,
                timezone=location.timezone,
            ),
        ),
    )


def search_policy_documents_data(query: str) -> PolicySearchResult:
    settings = get_settings()
    retriever = _retriever()
    result = retriever.search(query, top_k=settings.rag_top_k)
    validate_retrieved_hits(retriever.index, result.hits)
    matches = [_policy_evidence(hit.chunk, score=hit.score) for hit in result.hits]
    return PolicySearchResult(
        query=query,
        retrieval_mode=result.mode,
        index_version=retriever.index.index_version,
        evidence_rule=result.evidence_rule,
        sufficient_evidence=result.sufficient_evidence,
        matches=matches,
        missing_policy_ids=list(result.missing_policy_ids),
        conflicts=list(result.conflicts),
        limitation=result.limitation,
    )


def get_policy_section_data(policy_id: str, section_id: str) -> PolicySectionResult:
    index = _retriever().index
    chunks = index.section(policy_id, section_id)
    evidence = [_policy_evidence(chunk, score=1.0) for chunk in chunks]
    conflicts: list[str] = []
    if len({chunk.version for chunk in chunks}) > 1:
        conflicts.append(f"multiple versions found for {policy_id} {section_id}")
    return PolicySectionResult(
        policy_id=policy_id,
        section_id=section_id,
        found=bool(evidence),
        index_version=index.index_version,
        evidence=evidence,
        conflicts=conflicts,
        limitation=(
            "Exact section evidence from the committed synthetic corpus; it is not legal advice."
        ),
    )


def check_pto_balance_data(
    employee_id: str,
    request_start: date,
    request_end: date,
) -> PTOBalanceResult:
    bundle = load_seed_bundle()
    requested_workdays = _business_days(request_start, request_end)
    balance = next(
        (item for item in bundle.pto_balances if item.employee_id == employee_id),
        None,
    )
    if balance is None:
        return PTOBalanceResult(
            employee_id=employee_id,
            as_of_date=bundle.manifest.as_of_date,
            found=False,
            request_start=request_start,
            request_end=request_end,
            requested_workdays=requested_workdays,
            limitation="No synthetic PTO record was found; no balance was inferred.",
        )

    requested_hours = balance.scheduled_hours_per_day * requested_workdays
    usable_hours = balance.available_hours - balance.pending_hours
    projected = usable_hours - requested_hours
    return PTOBalanceResult(
        employee_id=employee_id,
        as_of_date=bundle.manifest.as_of_date,
        found=True,
        eligible=balance.eligible,
        request_start=request_start,
        request_end=request_end,
        requested_workdays=requested_workdays,
        scheduled_hours_per_day=balance.scheduled_hours_per_day,
        requested_hours=requested_hours,
        available_hours=balance.available_hours,
        pending_hours=balance.pending_hours,
        projected_hours_after_request=projected,
        sufficient_balance=balance.eligible and projected >= 0,
        limitation=(
            "Read-only synthetic balance check. Sufficient hours do not constitute "
            "manager approval."
        ),
    )


def lookup_benefits_status_data(employee_id: str) -> BenefitsStatusResult:
    bundle = load_seed_bundle()
    record = next((item for item in bundle.benefits if item.employee_id == employee_id), None)
    if record is None:
        return BenefitsStatusResult(
            employee_id=employee_id,
            as_of_date=bundle.manifest.as_of_date,
            found=False,
            limitation="No synthetic benefits record was found; no status was inferred.",
        )
    return BenefitsStatusResult(
        employee_id=employee_id,
        as_of_date=bundle.manifest.as_of_date,
        found=True,
        eligibility_status=record.eligibility_status.value,
        enrollment_status=record.enrollment_status.value,
        plan_code=record.plan_code,
        coverage_tier=record.coverage_tier,
        effective_date=record.effective_date,
        limitation=(
            "Minimum-necessary synthetic enrollment status only; the insurer remains authoritative."
        ),
    )


def _section_refs(*values: tuple[str, str]) -> list[PolicySectionReference]:
    return [
        PolicySectionReference(policy_id=policy_id, section_id=section_id)
        for policy_id, section_id in values
    ]


def check_policy_compliance_data(
    workflow: str,
    employee_id: str | None,
    *,
    destination_country_code: str | None = None,
    duration_business_days: int | None = None,
    request_start: date | None = None,
    request_end: date | None = None,
    expense_amount: Decimal | None = None,
    currency: str | None = None,
) -> ComplianceCheckResult:
    bundle = load_seed_bundle()
    employee = next(
        (item for item in bundle.employees if item.employee_id == employee_id),
        None,
    )
    if employee_id is not None and employee is None:
        return ComplianceCheckResult(
            workflow=workflow,
            employee_id=employee_id,
            as_of_date=bundle.manifest.as_of_date,
            status="not_found",
            category="employee_not_found",
            required_policy_sections=[],
            clarification_needed=["Provide a valid synthetic employee ID."],
            calculation=ComplianceCalculation(),
            limitation="No employee facts or policy decision were inferred.",
        )

    if workflow == "international_remote_work":
        refs = _section_refs(
            ("POL-INT-001", "INT-4"),
            ("POL-INT-001", "INT-5"),
            ("POL-INT-001", "INT-13"),
            ("POL-RWK-001", "RWK-5"),
            ("POL-SEC-001", "SEC-8"),
        )
        missing = []
        if destination_country_code is None:
            missing.append("destination country code")
        if duration_business_days is None:
            missing.append("expected business days worked")
        if missing:
            return ComplianceCheckResult(
                workflow=workflow,
                employee_id=employee_id,
                as_of_date=bundle.manifest.as_of_date,
                status="needs_clarification",
                category="incomplete_request",
                required_policy_sections=refs,
                clarification_needed=missing,
                calculation=ComplianceCalculation(business_days=duration_business_days),
                limitation="A deterministic eligibility screen is not an approval.",
            )
        assert duration_business_days is not None
        if duration_business_days <= 0:
            raise ValueError("duration_business_days must be greater than zero")
        country_code = str(destination_country_code).upper()
        if len(country_code) != 2:
            raise ValueError("destination_country_code must be a two-letter code")
        if country_code != "DE":
            return ComplianceCheckResult(
                workflow=workflow,
                employee_id=employee_id,
                as_of_date=bundle.manifest.as_of_date,
                status="needs_clarification",
                category="country_risk_unclassified",
                required_policy_sections=refs,
                clarification_needed=["country-risk classification for the destination"],
                calculation=ComplianceCalculation(business_days=duration_business_days),
                limitation=(
                    "No country-risk classification was inferred; a deterministic eligibility "
                    "screen is not an approval."
                ),
            )
        baseline_eligible = employee is None or (
            employee.status.value == "active"
            and employee.employment_type.value in {"RFT", "RPT"}
            and (bundle.manifest.as_of_date - employee.hire_date).days >= 90
        )
        if not baseline_eligible or duration_business_days > 30:
            category = (
                "assignment_or_location_change"
                if duration_business_days > 30
                else "baseline_ineligible"
            )
            return ComplianceCheckResult(
                workflow=workflow,
                employee_id=employee_id,
                as_of_date=bundle.manifest.as_of_date,
                status="not_eligible",
                category=category,
                required_policy_sections=refs,
                conditions=[
                    "Use the formal mobility or employment-location process."
                    if duration_business_days > 30
                    else "Baseline employment and service criteria are not met."
                ],
                calculation=ComplianceCalculation(business_days=duration_business_days),
                limitation="A deterministic eligibility screen is not an approval.",
            )
        exceptional = duration_business_days >= 21
        approvals = [
            "Manager",
            "Director",
            "People Operations",
            "Security",
            "Finance/Tax",
        ]
        if exceptional:
            approvals.extend(["VP sponsor", "Legal"])
        return ComplianceCheckResult(
            workflow=workflow,
            employee_id=employee_id,
            as_of_date=bundle.manifest.as_of_date,
            status="conditionally_eligible",
            category=("international_exceptional" if exceptional else "international_short_term"),
            required_approvals=approvals,
            required_policy_sections=refs,
            conditions=[
                "Confirm destination risk classification and cumulative international days.",
                "Confirm lawful work status, security controls, time-zone overlap, and "
                "business feasibility.",
                f"Submit at least {30 if exceptional else 20} business days in advance.",
            ],
            calculation=ComplianceCalculation(business_days=duration_business_days),
            limitation="Conditional eligibility is not approval to work from the destination.",
        )

    if workflow == "pto_request":
        if employee_id is None:
            raise ValueError("pto_request compliance requires employee_id")
        refs = _section_refs(("POL-PTO-001", "PTO-6"), ("POL-PTO-001", "PTO-7"))
        if request_start is None or request_end is None:
            missing = []
            if request_start is None:
                missing.append("exact start date")
            if request_end is None:
                missing.append("exact end date")
            return ComplianceCheckResult(
                workflow=workflow,
                employee_id=employee_id,
                as_of_date=bundle.manifest.as_of_date,
                status="needs_clarification",
                category="incomplete_request",
                required_policy_sections=refs,
                clarification_needed=missing,
                calculation=ComplianceCalculation(),
                limitation="A PTO eligibility screen cannot approve or modify a request.",
            )
        balance = check_pto_balance_data(employee_id, request_start, request_end)
        workdays = balance.requested_workdays
        notice = 5 if workdays <= 2 else 10 if workdays <= 5 else 20
        eligible = bool(balance.eligible and balance.sufficient_balance and workdays > 0)
        return ComplianceCheckResult(
            workflow=workflow,
            employee_id=employee_id,
            as_of_date=bundle.manifest.as_of_date,
            status="conditionally_eligible" if eligible else "not_eligible",
            category="pto_balance_and_notice_check" if eligible else "pto_balance_not_sufficient",
            required_approvals=["Manager"],
            required_policy_sections=refs,
            conditions=[
                f"Submit with at least {notice} business days of normal notice.",
                "Manager approval remains subject to coverage and scheduling criteria.",
            ],
            calculation=ComplianceCalculation(
                business_days=workdays,
                requested_hours=balance.requested_hours,
                available_hours=balance.available_hours,
                normal_notice_business_days=notice,
            ),
            limitation="A PTO eligibility screen cannot approve or modify a request.",
        )

    if workflow == "home_office_expense":
        refs = _section_refs(
            ("POL-EQP-001", "EQP-4"),
            ("POL-EXP-001", "EXP-3"),
            ("POL-EXP-001", "EXP-7"),
        )
        missing = []
        if expense_amount is None:
            missing.append("expense amount")
        if currency is None:
            missing.append("expense currency")
        if missing:
            return ComplianceCheckResult(
                workflow=workflow,
                employee_id=employee_id,
                as_of_date=bundle.manifest.as_of_date,
                status="needs_clarification",
                category="incomplete_request",
                required_policy_sections=refs,
                clarification_needed=missing,
                calculation=ComplianceCalculation(expense_amount=expense_amount),
                limitation="This screen does not reimburse or preapprove an expense.",
            )
        amount = Decimal(expense_amount)
        if amount < 0:
            raise ValueError("expense_amount cannot be negative")
        normalized_currency = str(currency).upper()
        if normalized_currency not in {"CAD", "USD"}:
            raise ValueError("currency must be CAD or USD")
        cap = Decimal("500") if normalized_currency == "CAD" else Decimal("375")
        executive_threshold = (
            Decimal("2500") if normalized_currency == "CAD" else Decimal("1875")
        )
        approvals = ["Manager"]
        if amount >= executive_threshold:
            approvals.extend(["VP", "Finance"])
        elif amount >= cap:
            approvals.append("Director or designated budget owner")
        eligible = employee is None or (
            employee.employment_type.value in {"RFT", "RPT"}
            and employee.remote_work_classification.value in {"hybrid", "remote"}
        )
        remainder = max(Decimal("0"), amount - cap)
        return ComplianceCheckResult(
            workflow=workflow,
            employee_id=employee_id,
            as_of_date=bundle.manifest.as_of_date,
            status="conditionally_eligible" if eligible else "not_eligible",
            category=("ordinary_cap_partial" if remainder > 0 else "within_ordinary_cap"),
            required_approvals=approvals,
            required_policy_sections=refs,
            conditions=[
                "Preapproval is required before purchase.",
                "The employee pays any amount above the ordinary cap unless an approved "
                "accommodation applies.",
            ],
            calculation=ComplianceCalculation(
                expense_amount=amount,
                currency=normalized_currency,
                ordinary_reimbursement_cap=cap,
                employee_paid_remainder=remainder,
            ),
            limitation="This screen does not reimburse or preapprove an expense.",
        )

    raise ValueError(f"unsupported compliance workflow: {workflow}")


def draft_hr_email_data(
    draft_type: str,
    employee_id: str,
    *,
    request_start: date | None = None,
    request_end: date | None = None,
    context: str | None = None,
) -> HREmailDraftResult:
    bundle = load_seed_bundle()
    employee = next((item for item in bundle.employees if item.employee_id == employee_id), None)
    if employee is None:
        raise ValueError(f"synthetic employee {employee_id} was not found")
    manager = next(
        (item for item in bundle.employees if item.employee_id == employee.manager_id),
        None,
    )
    recipient = manager.synthetic_name if manager else "People Operations"

    if draft_type == "pto_manager_request":
        if request_start is None or request_end is None:
            raise ValueError("PTO drafts require exact request_start and request_end dates")
        if request_end < request_start:
            raise ValueError("request_end must be on or after request_start")
        subject = f"PTO request: {request_start.isoformat()} to {request_end.isoformat()}"
        body = (
            f"Hi {recipient},\n\n"
            f"I would like to request PTO from {request_start.isoformat()} through "
            f"{request_end.isoformat()}. I will add the request to the approved HR system and "
            "coordinate a coverage plan. Please let me know if we should discuss any scheduling "
            "conflicts.\n\nThank you,\n"
            f"{employee.synthetic_name}"
        )
    elif draft_type == "peopleops_follow_up":
        subject = "People Operations follow-up"
        body = (
            "Hello People Operations,\n\n"
            f"I am following up on a PeopleOps question for synthetic employee {employee_id}. "
            f"{context or 'Please advise on the appropriate next step.'}\n\n"
            f"Thank you,\n{employee.synthetic_name}"
        )
    elif draft_type == "case_acknowledgement":
        subject = "Acknowledgement of your People Operations report"
        body = (
            f"Hello {employee.synthetic_name},\n\n"
            "We received your report and will route it for controlled review. This acknowledgement "
            "does not make a finding. Please share only information necessary for the review and "
            "contact emergency services if anyone is in immediate danger.\n\nPeople Operations"
        )
    else:
        raise ValueError(f"unsupported draft type: {draft_type}")

    fingerprint = hashlib.sha256(
        f"{draft_type}|{employee_id}|{subject}|{body}".encode()
    ).hexdigest()[:12].upper()
    return HREmailDraftResult(
        draft_id=f"DRAFT-{fingerprint}",
        draft_type=draft_type,
        employee_id=employee_id,
        subject=subject,
        body=body,
        warnings=[
            "Draft only - no email was sent.",
            "Review recipients, dates, policy citations, and sensitive details before use.",
        ],
    )


def create_mock_hr_ticket_data(
    category: str,
    priority: str,
    summary: str,
    affected_employee_id: str,
    idempotency_key: str,
    confirmation_token: str,
) -> MockTicketActionResult:
    return mock_ticket_actions.create(
        category=category,
        priority=priority,
        summary=summary,
        affected_employee_id=affected_employee_id,
        idempotency_key=idempotency_key,
        confirmation_token=confirmation_token,
    )
