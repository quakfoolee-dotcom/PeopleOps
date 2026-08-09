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
    r"\b(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+(\d{1,2})(?:,?\s+(20\d{2}))?\b",
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
}


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


class UnsupportedIntent(ContractModel):
    kind: Literal[WorkflowKind.UNSUPPORTED] = WorkflowKind.UNSUPPORTED
    refusal: bool = False
    reason: str
    clarification_needed: list[str] = Field(default_factory=list)


WorkflowIntent = RemoteWorkIntent | PTOIntent | ExpenseIntent | TicketIntent | UnsupportedIntent


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
        {WorkflowStage.PROFILE, WorkflowStage.ESCALATE, WorkflowStage.RESPOND}
    ),
    WorkflowStage.PROFILE: frozenset(
        {WorkflowStage.RETRIEVE, WorkflowStage.CLARIFY, WorkflowStage.ESCALATE}
    ),
    WorkflowStage.RETRIEVE: frozenset({WorkflowStage.EVIDENCE, WorkflowStage.ESCALATE}),
    WorkflowStage.EVIDENCE: frozenset(
        {
            WorkflowStage.COMPLIANCE,
            WorkflowStage.CONFIRMATION,
            WorkflowStage.ACTION,
            WorkflowStage.ESCALATE,
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
        if re.search(rf"\b{re.escape(name)}\b", normalized):
            return result
    return None, None


def classify_request(message: str, supplied_employee_id: str | None) -> WorkflowIntent:
    normalized = message.casefold()
    employee_id, employee_clarifications = _employee_id(message, supplied_employee_id)

    if ("diagnose" in normalized or "diagnosis" in normalized) and "legal" in normalized:
        return UnsupportedIntent(
            refusal=True,
            reason=(
                "medical diagnosis and definitive legal advice are outside this assistant's scope"
            ),
        )

    if "ticket" in normalized or "hr case" in normalized:
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

    if any(
        phrase in normalized
        for phrase in ("pto", "vacation", "time off", "take next week off")
    ):
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

    if any(
        phrase in normalized
        for phrase in ("reimburs", "home-office", "home office", "expense", "chair")
    ):
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

    if any(
        phrase in normalized
        for phrase in ("work remotely", "remote work", "work from", "work overseas", "overseas")
    ):
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
            "Phase 7 supports international remote-work eligibility, PTO guidance, "
            "home-office expense compliance, and confirmation-gated mock HR tickets"
        )
    )
