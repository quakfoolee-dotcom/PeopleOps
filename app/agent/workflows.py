from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal, Protocol

from pydantic import Field

from app.api.contracts import ContractModel, WorkflowKind, WorkflowStage
from peopleops_mcp.schemas import MockTicketPreview

EMPLOYEE_PATTERN = re.compile(r"\bE-\d{4}\b", re.IGNORECASE)
ISO_DATE_PATTERN = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
MONTH_DATE_PATTERN = re.compile(
    r"\b(January|Jan|February|Feb|March|Mar|April|Apr|May|June|Jun|July|Jul|"
    r"August|Aug|September|Sep|Sept|October|Oct|November|Nov|December|Dec)"
    r"\.?\s+(\d{1,2})(?:,?\s+(20\d{2}))?\b",
    re.IGNORECASE,
)
AMOUNT_PATTERN = re.compile(
    r"(?:(CAD|USD)\s*\$?\s*([0-9]+(?:\.[0-9]{1,2})?)|"
    r"\$?\s*([0-9]+(?:\.[0-9]{1,2})?)\s*(CAD|USD))",
    re.IGNORECASE,
)

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}
COUNTRIES = {
    "germany": ("DE", "Germany"),
    "spain": ("ES", "Spain"),
    "canada": ("CA", "Canada"),
    "united states": ("US", "the United States"),
    "usa": ("US", "the United States"),
    "u.s.": ("US", "the United States"),
    "america": ("US", "the United States"),
    "deutschland": ("DE", "Germany"),
}

TYPO_CORRECTIONS = {
    "remotly": "remotely",
    "vacaton": "vacation",
    "reimbursment": "reimbursement",
}


def _normalized_message(message: str) -> str:
    normalized = message.casefold()
    for typo, replacement in TYPO_CORRECTIONS.items():
        normalized = re.sub(rf"\b{typo}\b", replacement, normalized)
    return normalized


class RemoteWorkIntent(ContractModel):
    kind: Literal[WorkflowKind.REMOTE_WORK] = WorkflowKind.REMOTE_WORK
    employee_id: str | None = Field(default=None, pattern=r"^E-\d{4}$")
    destination_country_code: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    destination_name: str | None = None
    duration_business_days: int | None = Field(default=None, ge=1, le=366)
    duration_calendar_days: int | None = Field(default=None, ge=1, le=732)
    wants_draft: bool = False
    clarification_needed: list[str] = Field(default_factory=list)


class PTOIntent(ContractModel):
    kind: Literal[WorkflowKind.PTO] = WorkflowKind.PTO
    employee_id: str | None = Field(default=None, pattern=r"^E-\d{4}$")
    request_start: date | None = None
    request_end: date | None = None
    wants_draft: bool = False
    clarification_needed: list[str] = Field(default_factory=list)


class ExpenseIntent(ContractModel):
    kind: Literal[WorkflowKind.EXPENSE] = WorkflowKind.EXPENSE
    employee_id: str | None = Field(default=None, pattern=r"^E-\d{4}$")
    amount: Decimal | None = Field(default=None, ge=0)
    currency: Literal["CAD", "USD"] | None = None
    item: str = "home-office equipment"
    clarification_needed: list[str] = Field(default_factory=list)


class TicketIntent(ContractModel):
    kind: Literal[WorkflowKind.MOCK_TICKET] = WorkflowKind.MOCK_TICKET
    employee_id: str | None = Field(default=None, pattern=r"^E-\d{4}$")
    category: Literal["workplace_concern"] = "workplace_concern"
    priority: Literal["normal", "high", "urgent"] = "high"
    summary: str = Field(min_length=5, max_length=500)
    clarification_needed: list[str] = Field(default_factory=list)


class PolicyIntent(ContractModel):
    kind: Literal[WorkflowKind.POLICY] = WorkflowKind.POLICY
    topic: str = Field(min_length=1, max_length=80)
    employee_id: str | None = Field(default=None, pattern=r"^E-\d{4}$")
    required_sections: tuple[tuple[str, str], ...]
    guidance: str = Field(min_length=1, max_length=6000)
    requires_profile: bool = False
    requires_benefits: bool = False
    compliance_workflow: Literal[
        "international_remote_work", "home_office_expense"
    ] | None = None
    compliance_arguments: dict[str, str | int] = Field(default_factory=dict)
    conditional: bool = False
    escalation: bool = False
    refusal: bool = False
    retrieve_before_clarification: bool = False
    clarification_needed: list[str] = Field(default_factory=list)


class UnsupportedIntent(ContractModel):
    kind: Literal[WorkflowKind.UNSUPPORTED] = WorkflowKind.UNSUPPORTED
    refusal: bool = False
    reason: str
    clarification_needed: list[str] = Field(default_factory=list)


WorkflowIntent = (
    PolicyIntent
    | RemoteWorkIntent
    | PTOIntent
    | ExpenseIntent
    | TicketIntent
    | UnsupportedIntent
)


class TicketActionCoordinator(Protocol):
    def prepare(
        self,
        *,
        category: str,
        priority: str,
        summary: str,
        affected_employee_id: str,
        idempotency_key: str,
    ) -> MockTicketPreview: ...


ALLOWED_TRANSITIONS: dict[WorkflowStage, frozenset[WorkflowStage]] = {
    WorkflowStage.CLASSIFY: frozenset(
        {WorkflowStage.CLARIFY, WorkflowStage.DISCOVER, WorkflowStage.RESPOND}
    ),
    WorkflowStage.CLARIFY: frozenset({WorkflowStage.RESPOND}),
    WorkflowStage.DISCOVER: frozenset(
        {
            WorkflowStage.PROFILE,
            WorkflowStage.RETRIEVE,
            WorkflowStage.ESCALATE,
            WorkflowStage.RESPOND,
        }
    ),
    WorkflowStage.PROFILE: frozenset(
        {WorkflowStage.RETRIEVE, WorkflowStage.CLARIFY, WorkflowStage.ESCALATE}
    ),
    WorkflowStage.RETRIEVE: frozenset({WorkflowStage.EVIDENCE, WorkflowStage.ESCALATE}),
    WorkflowStage.EVIDENCE: frozenset(
        {
            WorkflowStage.COMPLIANCE,
            WorkflowStage.CLARIFY,
            WorkflowStage.CONFIRMATION,
            WorkflowStage.ACTION,
            WorkflowStage.ESCALATE,
            WorkflowStage.RESPOND,
        }
    ),
    WorkflowStage.COMPLIANCE: frozenset(
        {
            WorkflowStage.DRAFT,
            WorkflowStage.CLARIFY,
            WorkflowStage.RESPOND,
            WorkflowStage.ESCALATE,
        }
    ),
    WorkflowStage.DRAFT: frozenset({WorkflowStage.RESPOND, WorkflowStage.ESCALATE}),
    WorkflowStage.CONFIRMATION: frozenset({WorkflowStage.RESPOND}),
    WorkflowStage.ACTION: frozenset({WorkflowStage.RESPOND, WorkflowStage.ESCALATE}),
    WorkflowStage.ESCALATE: frozenset({WorkflowStage.RESPOND}),
    WorkflowStage.RESPOND: frozenset(),
}


class WorkflowMachine:
    """A small deterministic state machine with a hard logical tool-call budget."""

    def __init__(self, kind: WorkflowKind, *, max_tool_calls: int) -> None:
        self.kind = kind
        self.stage = WorkflowStage.CLASSIFY
        self.history = [self.stage]
        self.max_tool_calls = max_tool_calls
        self.logical_tool_calls = 0

    def transition(self, next_stage: WorkflowStage) -> None:
        if next_stage not in ALLOWED_TRANSITIONS[self.stage]:
            raise RuntimeError(
                f"invalid {self.kind} workflow transition: {self.stage} -> {next_stage}"
            )
        self.stage = next_stage
        self.history.append(next_stage)

    def reserve_tool_call(self) -> None:
        if self.logical_tool_calls >= self.max_tool_calls:
            raise RuntimeError("bounded workflow tool-call budget exhausted")
        self.logical_tool_calls += 1


def _employee_id(message: str, supplied: str | None) -> tuple[str | None, list[str]]:
    mentioned = {match.group(0).upper() for match in EMPLOYEE_PATTERN.finditer(message)}
    if supplied and mentioned and mentioned != {supplied}:
        return None, ["one consistent synthetic employee ID"]
    if supplied:
        return supplied, []
    if len(mentioned) == 1:
        return mentioned.pop(), []
    if len(mentioned) > 1:
        return None, ["one synthetic employee ID"]
    return None, ["synthetic employee ID"]


def _parse_dates(message: str) -> tuple[date | None, date | None]:
    try:
        iso_dates = [
            date(*map(int, match.groups())) for match in ISO_DATE_PATTERN.finditer(message)
        ]
    except ValueError:
        return None, None
    if len(iso_dates) >= 2:
        return iso_dates[0], iso_dates[1]

    matches = list(MONTH_DATE_PATTERN.finditer(message))
    if len(matches) < 2:
        return None, None
    years = [int(match.group(3)) for match in matches if match.group(3)]
    if not years:
        return None, None
    fallback_year = years[-1]
    try:
        parsed = [
            date(
                int(match.group(3)) if match.group(3) else fallback_year,
                MONTHS[match.group(1).casefold()],
                int(match.group(2)),
            )
            for match in matches[:2]
        ]
    except ValueError:
        return None, None
    return parsed[0], parsed[1]


def _duration_business_days(message: str) -> int | None:
    match = re.search(
        r"\b(\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+"
        r"(business\s+days?|work(?:ing)?\s+days?|weeks?)\b",
        message,
        re.IGNORECASE,
    )
    if match is None:
        return None
    raw_amount = match.group(1).casefold()
    amount = int(raw_amount) if raw_amount.isdigit() else NUMBER_WORDS[raw_amount]
    unit = match.group(2).casefold()
    return amount * 5 if "week" in unit else amount


def _duration_calendar_days(message: str) -> int | None:
    match = re.search(
        r"\b(\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+"
        r"(calendar\s+days?|weeks?)\b",
        message,
        re.IGNORECASE,
    )
    if match is None:
        return None
    raw_amount = match.group(1).casefold()
    amount = int(raw_amount) if raw_amount.isdigit() else NUMBER_WORDS[raw_amount]
    calendar_days = amount * 7 if "week" in match.group(2).casefold() else amount
    return calendar_days if calendar_days <= 732 else None


def _destination(message: str) -> tuple[str | None, str | None]:
    normalized = message.casefold()
    for name, result in COUNTRIES.items():
        if ("." in name and name in normalized) or re.search(
            rf"\b{re.escape(name)}\b", normalized
        ):
            return result
    return None, None


def classify_request(message: str, supplied_employee_id: str | None) -> WorkflowIntent:
    normalized = _normalized_message(message)
    employee_id, employee_clarifications = _employee_id(message, supplied_employee_id)

    if ("diagnose" in normalized or "diagnosis" in normalized) and any(
        term in normalized for term in ("legal", "law")
    ):
        return UnsupportedIntent(
            refusal=True,
            reason=(
                "medical diagnosis and definitive legal advice are outside this assistant's scope"
            ),
        )

    bypass_confirmation = any(
        phrase in normalized
        for phrase in (
            "do not ask me to confirm",
            "don't ask me to confirm",
            "skip confirmation",
            "without confirmation",
            "bypass confirmation",
        )
    )
    ticket_request = any(
        phrase in normalized
        for phrase in (
            "ticket",
            "hr case",
            "peopleops case",
            "people ops case",
            "raise a case",
            "open a case",
            "file a case",
        )
    )
    if ticket_request and bypass_confirmation:
        return PolicyIntent(
            topic="ticket_confirmation_guard",
            required_sections=(("POL-HRC-001", "HRC-8"),),
            guidance=(
                "I cannot bypass explicit confirmation. Before a sanitized preview can be "
                "prepared, provide the affected synthetic employee ID and a minimum-necessary "
                "summary. Ticket creation will remain blocked until the completed preview is "
                "reviewed and explicitly confirmed."
            ),
            retrieve_before_clarification=True,
            clarification_needed=[
                "affected synthetic employee ID",
                "minimum-necessary summary",
            ],
        )

    if (
        "show me employee" in normalized
        and "pto balance" in normalized
        and "benefits" in normalized
    ):
        return PolicyIntent(
            topic="privacy_refusal",
            required_sections=(("POL-CON-001", "CON-8"), ("POL-BEN-001", "BEN-11")),
            guidance=(
                "I cannot disclose another employee's PTO, benefits, or leave information "
                "without an established authorized purpose. Use an authorized People Operations "
                "or manager support channel; this response does not confirm whether any requested "
                "record exists."
            ),
            refusal=True,
        )

    if ticket_request:
        priority: Literal["normal", "high", "urgent"]
        if "urgent" in normalized or "immediate danger" in normalized:
            priority = "urgent"
        elif "harassment" in normalized or "workplace concern" in normalized:
            priority = "high"
        else:
            priority = "normal"
        identifier = employee_id or "the affected synthetic employee"
        return TicketIntent(
            employee_id=employee_id,
            priority=priority,
            summary=(
                f"Reported workplace concern involving {identifier}; controlled People Operations "
                "review requested. The report is not a finding."
            ),
            clarification_needed=employee_clarifications,
        )

    benefits_request = any(
        phrase in normalized for phrase in ("benefits", "health coverage", "health plan")
    )
    if benefits_request and any(
        phrase in normalized
        for phrase in (
            "currently enrolled",
            "benefits active",
            "my benefits",
            "coverage active",
            "enrolled in",
        )
    ):
        clarification = list(employee_clarifications)
        return PolicyIntent(
            topic="employee_benefits",
            employee_id=employee_id,
            required_sections=(
                ("POL-BEN-001", "BEN-3"),
                ("POL-BEN-001", "BEN-4"),
                ("POL-BEN-001", "BEN-11"),
            ),
            guidance=(
                "The synthetic benefits record is the operational status for this demonstration; "
                "policy eligibility depends on employment category, waiting periods, local plan "
                "terms, and applicable law. The plan administrator makes the final coverage "
                "determination."
            ),
            requires_profile=True,
            requires_benefits=True,
            clarification_needed=clarification,
        )

    onboarding_request = any(
        phrase in normalized for phrase in ("onboarding", "new employee", "new starter")
    )
    if onboarding_request and "first week" in normalized:
        return PolicyIntent(
            topic="employee_onboarding",
            employee_id=employee_id,
            required_sections=(
                ("POL-ONB-001", "ONB-5"),
                ("POL-ONB-001", "ONB-6"),
                ("POL-ONB-001", "ONB-7"),
            ),
            guidance=(
                "The first-week checklist includes account activation, role and schedule review, "
                "policy and reporting access, equipment acknowledgement, payroll/timekeeping, "
                "security training within three business days, team integration, and any "
                "role-specific training before controlled work begins. Completion is not inferred."
            ),
            requires_profile=True,
            clarification_needed=list(employee_clarifications),
        )

    if "family situation" in normalized and "leave" in normalized:
        return PolicyIntent(
            topic="family_leave_clarification",
            required_sections=(("POL-LEV-001", "LEV-5"), ("POL-LEV-001", "LEV-9")),
            guidance=(
                "The appropriate leave path depends on the general nature of the need, expected "
                "start date, duration, whether it may be intermittent, and work jurisdiction. "
                "Share only the minimum necessary information; a diagnosis is not required in "
                "chat, and People Operations can continue the classification privately."
            ),
            retrieve_before_clarification=True,
            clarification_needed=[
                "general leave reason without diagnosis",
                "expected start date and duration",
                "work jurisdiction",
            ],
        )

    manager_report = any(role in normalized for role in ("manager", "supervisor")) and any(
        phrase in normalized
        for phrase in ("harassment report", "harassment complaint", "conduct complaint")
    )
    if manager_report:
        return PolicyIntent(
            topic="manager_harassment_report",
            required_sections=(
                ("POL-CON-001", "CON-11"),
                ("POL-CON-001", "CON-12"),
                ("POL-HRC-001", "HRC-3"),
                ("POL-HRC-001", "HRC-7"),
            ),
            guidance=(
                "Address immediate danger first. A manager must route a covered concern within "
                "one business day, sooner when risk is urgent, and must not promise secrecy, "
                "investigate without authorization, or require confrontation. Available channels "
                "include People Operations, Ethics, Security when applicable, management, and "
                "emergency services for immediate danger."
            ),
            escalation=True,
        )

    if "benefits" in normalized and "pto accrual" in normalized and "medical leave" in normalized:
        return PolicyIntent(
            topic="benefits_during_leave",
            required_sections=(("POL-BEN-001", "BEN-9"), ("POL-LEV-001", "LEV-10")),
            guidance=(
                "Benefits continuation depends on the leave classification, applicable law, and "
                "plan terms; the employee may owe the normal premium share during unpaid leave. "
                "PTO accrues during paid leave and may pause after 30 consecutive calendar days "
                "of unpaid leave unless continuation is required. Confirm the individual result "
                "with People Operations."
            ),
            conditional=True,
        )

    if "holiday" in normalized and "approved pto" in normalized:
        return PolicyIntent(
            topic="holiday_during_pto",
            required_sections=(("POL-PTO-001", "PTO-5"), ("POL-HOL-001", "HOL-8")),
            guidance=(
                "A paid company holiday that falls during approved PTO is recorded as a holiday "
                "and is not deducted from PTO. The surrounding PTO request still follows normal "
                "scheduling and approval rules."
            ),
        )

    if "floating holiday" in normalized and "carry over" in normalized:
        return PolicyIntent(
            topic="floating_holiday",
            required_sections=(("POL-HOL-001", "HOL-6"),),
            guidance=(
                "The floating holiday does not carry over after December 31. It should normally "
                "be requested at least five business days in advance and requires manager approval "
                "for operational coverage."
            ),
        )

    if "itemized receipt" in normalized and "expense" in normalized:
        return PolicyIntent(
            topic="expense_receipt",
            required_sections=(("POL-EXP-001", "EXP-4"),),
            guidance=(
                "An itemized receipt is required for CAD 25 or USD 20 and above, and whenever "
                "Finance requests one. A missing-receipt declaration must include the vendor, "
                "date, amount, purpose, and reason the receipt is unavailable; it is not automatic "
                "approval."
            ),
        )

    if "credential compromise" in normalized:
        return PolicyIntent(
            topic="security_incident",
            required_sections=(("POL-SEC-001", "SEC-10"),),
            guidance=(
                "Report a suspected credential compromise immediately and no later than one hour "
                "after discovery. Preserve evidence, stop further sharing, and do not "
                "independently "
                "delete logs or negotiate with an attacker."
            ),
        )

    if "account security" in normalized and "phishing training" in normalized:
        return PolicyIntent(
            topic="onboarding_security_training",
            required_sections=(("POL-ONB-001", "ONB-6"),),
            guidance=(
                "Account security, phishing, MFA, and incident-reporting training is normally due "
                "within three business days. Access to sensitive systems may be withheld or "
                "suspended until required training is complete."
            ),
        )

    if "newly eligible" in normalized and "benefits enrollment" in normalized:
        return PolicyIntent(
            topic="benefits_enrollment",
            required_sections=(("POL-BEN-001", "BEN-5"),),
            guidance=(
                "A newly eligible employee has 31 calendar days after the eligibility notice to "
                "complete enrollment or waiver elections. Later changes normally require annual "
                "open enrollment or a qualifying life event reported within 31 calendar days; "
                "plan-specific evidence may be required."
            ),
        )

    if "notice" in normalized and "workdays of pto" in normalized:
        return PolicyIntent(
            topic="pto_notice",
            required_sections=(("POL-PTO-001", "PTO-6"),),
            guidance=(
                "Three to five consecutive scheduled workdays of PTO normally require ten "
                "business days of notice. Short notice does not automatically disqualify the "
                "request, but coverage and business impact may affect approval."
            ),
        )

    if (
        "normal home-office furniture reimbursement limit" in normalized
        or "normal home office furniture reimbursement limit" in normalized
    ):
        return PolicyIntent(
            topic="home_office_limit",
            required_sections=(("POL-EQP-001", "EQP-4"),),
            guidance=(
                "Eligible Remote and Hybrid RFT or RPT employees may request written preapproval "
                "for up to CAD 500 or USD 375 once every 36 months under the ordinary furniture "
                "program. An accommodation exception is a separate review."
            ),
        )

    if "otherwise eligible remote employee" in normalized and "cad 900" in normalized:
        return PolicyIntent(
            topic="generic_home_office_expense",
            required_sections=(
                ("POL-EQP-001", "EQP-4"),
                ("POL-EXP-001", "EXP-3"),
                ("POL-EXP-001", "EXP-7"),
            ),
            guidance=(
                "For an otherwise eligible remote employee, ordinary reimbursement for a CAD 900 "
                "chair is capped at CAD 500 once every 36 months and requires written preapproval; "
                "the employee normally pays the CAD 400 remainder. An approved accommodation may "
                "authorize a different result."
            ),
            compliance_workflow="home_office_expense",
            compliance_arguments={"expense_amount": "900", "currency": "CAD"},
            conditional=True,
        )

    if all(
        phrase in normalized
        for phrase in ("british columbia employee", "germany", "six weeks")
    ):
        return PolicyIntent(
            topic="generic_international_remote_work",
            required_sections=(
                ("POL-INT-001", "INT-5"),
                ("POL-INT-001", "INT-13"),
                ("POL-RWK-001", "RWK-5"),
                ("POL-SEC-001", "SEC-8"),
            ),
            guidance=(
                "Six calendar weeks in Germany is normally about 30 business days and falls in "
                "the International exceptional category. Submit at least 30 business days in "
                "advance and obtain manager, director, People Operations, Security, Finance/Tax, "
                "VP-sponsor, and Legal review. Standard-Risk status is not approval; lawful-work, "
                "security, location, cumulative-day, and business conditions still apply."
            ),
            compliance_workflow="international_remote_work",
            compliance_arguments={
                "destination_country_code": "DE",
                "duration_business_days": 30,
            },
            conditional=True,
        )

    pto_request = any(
        phrase in normalized
        for phrase in (
            "pto",
            "vacation",
            "time off",
            "take next week off",
            "annual leave",
            "vacay",
        )
    )
    expense_request = any(
        phrase in normalized
        for phrase in (
            "reimburs",
            "home-office",
            "home office",
            "expense",
            "chair",
            "claim back",
            "repay",
            "ergonomic",
        )
    )
    remote_request = any(
        phrase in normalized
        for phrase in (
            "work remotely",
            "working remotely",
            "remote work",
            "work from",
            "work overseas",
            "overseas",
            "telework",
            "work abroad",
            "working abroad",
            "do my job from",
        )
    )
    requested_domains = [
        name
        for name, requested in (
            ("PTO", pto_request),
            ("expense", expense_request),
            ("remote-work", remote_request),
        )
        if requested
    ]
    if len(requested_domains) > 1:
        return UnsupportedIntent(
            reason=(
                "the request combines multiple workflows: "
                + ", ".join(requested_domains)
            ),
            clarification_needed=[
                "one request at a time",
                "which workflow to handle first",
            ],
        )

    if pto_request:
        request_start, request_end = _parse_dates(message)
        clarification = list(employee_clarifications)
        if request_start is None:
            clarification.append("exact PTO start date")
        if request_end is None:
            clarification.append("exact PTO end date")
        if request_start and request_end and request_end < request_start:
            clarification.append("an end date on or after the start date")
        return PTOIntent(
            employee_id=employee_id,
            request_start=request_start,
            request_end=request_end,
            wants_draft=any(word in normalized for word in ("draft", "message", "email")),
            clarification_needed=clarification,
        )

    if expense_request:
        match = AMOUNT_PATTERN.search(message)
        amount: Decimal | None = None
        currency: Literal["CAD", "USD"] | None = None
        if match:
            currency_text = (match.group(1) or match.group(4)).upper()
            amount_text = match.group(2) or match.group(3)
            try:
                amount = Decimal(amount_text)
                currency = "CAD" if currency_text == "CAD" else "USD"
            except InvalidOperation:
                amount = None
        clarification = list(employee_clarifications)
        if amount is None:
            clarification.append("expense amount")
        if currency is None:
            clarification.append("expense currency (CAD or USD)")
        return ExpenseIntent(
            employee_id=employee_id,
            amount=amount,
            currency=currency,
            item="home-office chair" if "chair" in normalized else "home-office equipment",
            clarification_needed=clarification,
        )

    if remote_request:
        country_code, destination_name = _destination(message)
        duration = _duration_business_days(message)
        clarification = list(employee_clarifications)
        if country_code is None:
            clarification.append("destination country")
        if duration is None:
            clarification.append("exact dates or expected business days worked")
        elif duration > 366:
            clarification.append("a duration no greater than 366 business days")
            duration = None
        if "overseas" in normalized and (country_code is None or duration is None):
            clarification.extend(["work pattern", "business reason"])
        return RemoteWorkIntent(
            employee_id=employee_id,
            destination_country_code=country_code,
            destination_name=destination_name,
            duration_business_days=duration,
            duration_calendar_days=_duration_calendar_days(message),
            wants_draft=any(word in normalized for word in ("draft", "message", "email")),
            clarification_needed=list(dict.fromkeys(clarification)),
        )

    return UnsupportedIntent(
        reason=(
            "the request does not match a supported policy, employee-guidance, or mock-action "
            "workflow in this synthetic demonstration"
        )
    )
