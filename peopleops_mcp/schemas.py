from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MCPModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EmployeeLocation(MCPModel):
    location_id: str
    name: str
    city: str
    province_or_state: str
    country_code: str
    timezone: str


class EmployeeProfile(MCPModel):
    employee_id: str
    synthetic_name: str
    employment_type: str
    role: str
    department: str
    manager_id: str | None
    remote_work_classification: str
    employment_status: str
    hire_date: date
    home_office: EmployeeLocation


class EmployeeProfileResult(MCPModel):
    employee_id: str
    as_of_date: date
    found: bool
    profile: EmployeeProfile | None = None


class PolicyEvidence(MCPModel):
    policy_id: str = Field(pattern=r"^POL-[A-Z]{3}-\d{3}$")
    section_id: str = Field(pattern=r"^[A-Z]{3}-\d+(?:\.\d+)?$")
    title: str
    snippet: str = Field(min_length=1, max_length=1000)
    version: str
    effective_date: date
    source_format: Literal["markdown", "pdf"]
    source_path: str
    page: int | None = Field(default=None, ge=1)
    chunk_id: str = Field(pattern=r"^POL-[A-Z]{3}-\d{3}::[A-Z]{3}-\d+(?:\.\d+)?::\d{2}$")
    retrieval_score: float = Field(ge=0, le=1)


class PolicySearchResult(MCPModel):
    query: str
    retrieval_mode: Literal["phase5_hybrid", "phase5_dense", "phase5_keyword"]
    index_version: str
    evidence_rule: str
    sufficient_evidence: bool
    matches: list[PolicyEvidence]
    missing_policy_ids: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    limitation: str


class PolicySectionResult(MCPModel):
    policy_id: str = Field(pattern=r"^POL-[A-Z]{3}-\d{3}$")
    section_id: str = Field(pattern=r"^[A-Z]{3}-\d+(?:\.\d+)?$")
    found: bool
    index_version: str
    evidence: list[PolicyEvidence] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    limitation: str

    @model_validator(mode="after")
    def enforce_found_evidence_consistency(self) -> "PolicySectionResult":
        if self.found != bool(self.evidence):
            raise ValueError("found must match whether exact section evidence is present")
        return self


class PTOBalanceResult(MCPModel):
    employee_id: str = Field(pattern=r"^E-\d{4}$")
    as_of_date: date
    found: bool
    eligible: bool | None = None
    request_start: date
    request_end: date
    requested_workdays: int = Field(ge=0, le=366)
    scheduled_hours_per_day: Decimal | None = Field(default=None, ge=0)
    requested_hours: Decimal | None = Field(default=None, ge=0)
    available_hours: Decimal | None = Field(default=None, ge=0)
    pending_hours: Decimal | None = Field(default=None, ge=0)
    projected_hours_after_request: Decimal | None = None
    sufficient_balance: bool | None = None
    approval_required: Literal[True] = True
    limitation: str

    @model_validator(mode="after")
    def validate_result_shape(self) -> "PTOBalanceResult":
        if self.request_end < self.request_start:
            raise ValueError("request_end must be on or after request_start")
        data_fields = (
            self.eligible,
            self.scheduled_hours_per_day,
            self.requested_hours,
            self.available_hours,
            self.pending_hours,
            self.projected_hours_after_request,
            self.sufficient_balance,
        )
        if self.found and any(value is None for value in data_fields):
            raise ValueError("found PTO results require balance and calculation fields")
        if not self.found and any(value is not None for value in data_fields):
            raise ValueError("unknown employees cannot return PTO data")
        return self


class BenefitsStatusResult(MCPModel):
    employee_id: str = Field(pattern=r"^E-\d{4}$")
    as_of_date: date
    found: bool
    eligibility_status: Literal["eligible", "ineligible"] | None = None
    enrollment_status: Literal["enrolled", "waived", "pending", "not_eligible"] | None = None
    plan_code: str | None = None
    coverage_tier: Literal["employee", "employee_plus_one", "family"] | None = None
    effective_date: date | None = None
    minimum_necessary: Literal[True] = True
    limitation: str

    @model_validator(mode="after")
    def validate_found_status(self) -> "BenefitsStatusResult":
        if self.found and (
            self.eligibility_status is None or self.enrollment_status is None
        ):
            raise ValueError("found benefits results require eligibility and enrollment status")
        if not self.found and any(
            value is not None
            for value in (
                self.eligibility_status,
                self.enrollment_status,
                self.plan_code,
                self.coverage_tier,
                self.effective_date,
            )
        ):
            raise ValueError("unknown employees cannot return benefits data")
        return self


class PolicySectionReference(MCPModel):
    policy_id: str = Field(pattern=r"^POL-[A-Z]{3}-\d{3}$")
    section_id: str = Field(pattern=r"^[A-Z]{3}-\d+(?:\.\d+)?$")


class ComplianceCalculation(MCPModel):
    business_days: int | None = Field(default=None, ge=0)
    requested_hours: Decimal | None = Field(default=None, ge=0)
    available_hours: Decimal | None = Field(default=None, ge=0)
    normal_notice_business_days: int | None = Field(default=None, ge=0)
    expense_amount: Decimal | None = Field(default=None, ge=0)
    currency: Literal["CAD", "USD"] | None = None
    ordinary_reimbursement_cap: Decimal | None = Field(default=None, ge=0)
    employee_paid_remainder: Decimal | None = Field(default=None, ge=0)


class ComplianceCheckResult(MCPModel):
    workflow: Literal["international_remote_work", "pto_request", "home_office_expense"]
    employee_id: str | None = Field(default=None, pattern=r"^E-\d{4}$")
    as_of_date: date
    status: Literal[
        "conditionally_eligible", "not_eligible", "needs_clarification", "not_found"
    ]
    category: str = Field(min_length=1, max_length=120)
    required_approvals: list[str] = Field(default_factory=list)
    required_policy_sections: list[PolicySectionReference]
    conditions: list[str] = Field(default_factory=list)
    clarification_needed: list[str] = Field(default_factory=list)
    calculation: ComplianceCalculation
    decision_is_approval: Literal[False] = False
    limitation: str


class HREmailDraftResult(MCPModel):
    draft_id: str = Field(pattern=r"^DRAFT-[A-F0-9]{12}$")
    draft_type: Literal["pto_manager_request", "peopleops_follow_up", "case_acknowledgement"]
    employee_id: str = Field(pattern=r"^E-\d{4}$")
    label: Literal["Draft - not sent"] = "Draft - not sent"
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=4000)
    sent: Literal[False] = False
    persisted: Literal[False] = False
    warnings: list[str]


class MockTicketPreview(MCPModel):
    confirmation_id: str = Field(pattern=r"^PREVIEW-[A-F0-9]{16}$")
    category: Literal[
        "workplace_concern", "benefits", "leave", "payroll", "equipment", "onboarding", "other"
    ]
    priority: Literal["low", "normal", "high", "urgent"]
    summary: str = Field(min_length=5, max_length=500)
    affected_employee_id: str = Field(pattern=r"^E-\d{4}$")
    routing_team: str = Field(min_length=2, max_length=100)
    idempotency_key: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}$")
    expires_at: datetime
    confirmed: Literal[False] = False
    synthetic_only: Literal[True] = True


class MockTicketRecord(MCPModel):
    ticket_id: str = Field(pattern=r"^TKT-9\d{3}$")
    category: str
    priority: Literal["low", "normal", "high", "urgent"]
    summary: str
    affected_employee_id: str = Field(pattern=r"^E-\d{4}$")
    routing_team: str
    status: Literal["open"] = "open"
    created_at: datetime
    confirmation_reference: str = Field(pattern=r"^CONF-9\d{3}$")


class MockTicketActionResult(MCPModel):
    action_status: Literal["created", "already_created"]
    ticket: MockTicketRecord
    synthetic_only: Literal[True] = True
    persistence: Literal["in_memory_until_restart"] = "in_memory_until_restart"
    limitation: str
