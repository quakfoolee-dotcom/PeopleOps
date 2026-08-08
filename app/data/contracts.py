from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator, model_validator


class DataModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EmploymentType(StrEnum):
    REGULAR_FULL_TIME = "RFT"
    REGULAR_PART_TIME = "RPT"
    TEMPORARY = "TEMP"
    CONTRACTOR = "CONTRACTOR"


class EmployeeStatus(StrEnum):
    ACTIVE = "active"
    LEAVE = "leave"
    INACTIVE = "inactive"


class RemoteWorkClassification(StrEnum):
    OFFICE = "office"
    HYBRID = "hybrid"
    REMOTE = "remote"


class Location(DataModel):
    location_id: str = Field(pattern=r"^LOC-[A-Z]{3}$")
    name: str = Field(min_length=1, max_length=120)
    city: str = Field(min_length=1, max_length=100)
    province_or_state: str = Field(min_length=2, max_length=100)
    country_code: Literal["CA", "US"]
    timezone: str = Field(pattern=r"^America/[A-Za-z_]+$")
    currency: Literal["CAD", "USD"]


class Employee(DataModel):
    employee_id: str = Field(pattern=r"^E-\d{4}$")
    synthetic_name: str = Field(min_length=3, max_length=120)
    employment_type: EmploymentType
    role: str = Field(min_length=2, max_length=120)
    department: str = Field(min_length=2, max_length=100)
    manager_id: str | None = Field(default=None, pattern=r"^E-\d{4}$")
    home_office_id: str = Field(pattern=r"^LOC-[A-Z]{3}$")
    hire_date: date
    remote_work_classification: RemoteWorkClassification
    status: EmployeeStatus
    weekly_hours: Decimal = Field(gt=0, le=40, decimal_places=2)

    @model_validator(mode="after")
    def reject_self_management(self) -> "Employee":
        if self.manager_id == self.employee_id:
            raise ValueError("an employee cannot manage themselves")
        return self


class ManagerRelationship(DataModel):
    employee_id: str = Field(pattern=r"^E-\d{4}$")
    manager_id: str = Field(pattern=r"^E-\d{4}$")
    effective_date: date

    @model_validator(mode="after")
    def reject_self_management(self) -> "ManagerRelationship":
        if self.manager_id == self.employee_id:
            raise ValueError("a manager relationship cannot reference the same employee")
        return self


class PTOBalance(DataModel):
    employee_id: str = Field(pattern=r"^E-\d{4}$")
    as_of_date: date
    eligible: bool
    available_hours: Decimal = Field(ge=0, decimal_places=2)
    pending_hours: Decimal = Field(ge=0, decimal_places=2)
    scheduled_hours_per_day: Decimal = Field(gt=0, le=12, decimal_places=2)

    @model_validator(mode="after")
    def require_zero_balance_when_ineligible(self) -> "PTOBalance":
        if not self.eligible and (self.available_hours != 0 or self.pending_hours != 0):
            raise ValueError("ineligible employees must have zero PTO balances")
        return self


class PTOTransactionType(StrEnum):
    ACCRUAL = "accrual"
    USAGE = "usage"
    ADJUSTMENT = "adjustment"
    CARRYOVER = "carryover"


class PTOTransaction(DataModel):
    transaction_id: str = Field(pattern=r"^PTO-TXN-\d{4}$")
    employee_id: str = Field(pattern=r"^E-\d{4}$")
    transaction_date: date
    transaction_type: PTOTransactionType
    hours_delta: Decimal = Field(decimal_places=2)
    note: str = Field(min_length=1, max_length=240)

    @field_validator("hours_delta")
    @classmethod
    def require_nonzero_delta(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("PTO transaction delta cannot be zero")
        return value


class BenefitsEligibility(StrEnum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"


class BenefitsEnrollment(StrEnum):
    ENROLLED = "enrolled"
    WAIVED = "waived"
    PENDING = "pending"
    NOT_ELIGIBLE = "not_eligible"


class BenefitsRecord(DataModel):
    employee_id: str = Field(pattern=r"^E-\d{4}$")
    as_of_date: date
    eligibility_status: BenefitsEligibility
    enrollment_status: BenefitsEnrollment
    plan_code: str | None = Field(default=None, pattern=r"^PLAN-[A-Z0-9-]+$")
    coverage_tier: Literal["employee", "employee_plus_one", "family"] | None = None
    effective_date: date | None = None

    @model_validator(mode="after")
    def enforce_eligibility_consistency(self) -> "BenefitsRecord":
        if self.eligibility_status is BenefitsEligibility.INELIGIBLE:
            if self.enrollment_status is not BenefitsEnrollment.NOT_ELIGIBLE:
                raise ValueError("ineligible employees must use not_eligible enrollment status")
            if self.plan_code is not None or self.coverage_tier is not None:
                raise ValueError("ineligible employees cannot have a plan or coverage tier")
        if self.enrollment_status is BenefitsEnrollment.ENROLLED and (
            self.plan_code is None or self.coverage_tier is None or self.effective_date is None
        ):
            raise ValueError("enrolled employees require plan, tier, and effective date")
        return self


class TicketPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class MockHRTicket(DataModel):
    ticket_id: str = Field(pattern=r"^TKT-\d{4}$")
    category: str = Field(min_length=2, max_length=80)
    priority: TicketPriority
    summary: str = Field(min_length=5, max_length=500)
    affected_employee_id: str = Field(pattern=r"^E-\d{4}$")
    routing_team: str = Field(min_length=2, max_length=100)
    status: TicketStatus
    created_at: datetime
    confirmation_reference: str = Field(pattern=r"^CONF-\d{4}$")

    @field_validator("created_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("ticket timestamps must include a timezone")
        return value


class DataFileDescriptor(DataModel):
    file_name: str = Field(pattern=r"^[a-z_]+\.json$")
    record_count: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class MockDataManifest(DataModel):
    schema_version: Literal["1.0"]
    organization: Literal["Northstar Technologies Inc."]
    synthetic_only: Literal[True]
    as_of_date: date
    files: dict[str, DataFileDescriptor]


class LocationDataset(RootModel[list[Location]]):
    pass


class EmployeeDataset(RootModel[list[Employee]]):
    pass


class ManagerRelationshipDataset(RootModel[list[ManagerRelationship]]):
    pass


class PTOBalanceDataset(RootModel[list[PTOBalance]]):
    pass


class PTOTransactionDataset(RootModel[list[PTOTransaction]]):
    pass


class BenefitsDataset(RootModel[list[BenefitsRecord]]):
    pass


class TicketDataset(RootModel[list[MockHRTicket]]):
    pass
