from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from mcp.server import MCPServer
from pydantic import Field

from peopleops_mcp.schemas import (
    BenefitsStatusResult,
    ComplianceCheckResult,
    EmployeeProfileResult,
    HREmailDraftResult,
    MockTicketActionResult,
    PolicySearchResult,
    PolicySectionResult,
    PTOBalanceResult,
)
from peopleops_mcp.tools import (
    check_policy_compliance_data,
    check_pto_balance_data,
    create_mock_hr_ticket_data,
    draft_hr_email_data,
    get_policy_section_data,
    lookup_benefits_status_data,
    lookup_employee_profile_data,
    search_policy_documents_data,
)

EmployeeId = Annotated[str, Field(pattern=r"^E-\d{4}$")]
PolicyId = Annotated[str, Field(pattern=r"^POL-[A-Z]{3}-\d{3}$")]
SectionId = Annotated[str, Field(pattern=r"^[A-Z]{3}-\d+(?:\.\d+)?$")]
IdempotencyKey = Annotated[
    str,
    Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}$"),
]

PHASE6_TOOL_NAMES = frozenset(
    {
        "search_policy_documents",
        "get_policy_section",
        "lookup_employee_profile",
        "check_pto_balance",
        "lookup_benefits_status",
        "check_policy_compliance",
        "draft_hr_email",
        "create_mock_hr_ticket",
    }
)

mcp_server = MCPServer(
    name="peopleops-assistant",
    title="PeopleOps Assistant MCP Server",
    description=(
        "Typed tools over synthetic PeopleOps policy and employee data, including one "
        "confirmation-gated in-memory mock action."
    ),
    version="0.3.0",
)


@mcp_server.tool(structured_output=True)
def search_policy_documents(
    query: Annotated[str, Field(min_length=2, max_length=4000)],
) -> PolicySearchResult:
    """Find citation-validated policy sections with the hybrid RAG index."""
    return search_policy_documents_data(query)


@mcp_server.tool(structured_output=True)
def get_policy_section(policy_id: PolicyId, section_id: SectionId) -> PolicySectionResult:
    """Return every authoritative chunk for one exact policy and section identifier."""
    return get_policy_section_data(policy_id, section_id)


@mcp_server.tool(structured_output=True)
def lookup_employee_profile(employee_id: EmployeeId) -> EmployeeProfileResult:
    """Return the minimum synthetic employee profile needed for PeopleOps guidance."""
    return lookup_employee_profile_data(employee_id)


@mcp_server.tool(structured_output=True)
def check_pto_balance(
    employee_id: EmployeeId,
    request_start: date,
    request_end: date,
) -> PTOBalanceResult:
    """Read a synthetic PTO balance and calculate requested weekdays and hours without mutation."""
    return check_pto_balance_data(employee_id, request_start, request_end)


@mcp_server.tool(structured_output=True)
def lookup_benefits_status(employee_id: EmployeeId) -> BenefitsStatusResult:
    """Return minimum-necessary synthetic benefits eligibility and enrollment status."""
    return lookup_benefits_status_data(employee_id)


@mcp_server.tool(structured_output=True)
def check_policy_compliance(
    workflow: Literal["international_remote_work", "pto_request", "home_office_expense"],
    employee_id: EmployeeId,
    destination_country_code: Annotated[
        str | None,
        Field(default=None, pattern=r"^[A-Za-z]{2}$"),
    ] = None,
    duration_business_days: Annotated[int | None, Field(default=None, ge=1, le=366)] = None,
    request_start: date | None = None,
    request_end: date | None = None,
    expense_amount: Annotated[Decimal | None, Field(default=None, ge=0)] = None,
    currency: Literal["CAD", "USD"] | None = None,
) -> ComplianceCheckResult:
    """Evaluate bounded deterministic rules; the result is guidance, never approval."""
    return check_policy_compliance_data(
        workflow,
        employee_id,
        destination_country_code=destination_country_code,
        duration_business_days=duration_business_days,
        request_start=request_start,
        request_end=request_end,
        expense_amount=expense_amount,
        currency=currency,
    )


@mcp_server.tool(structured_output=True)
def draft_hr_email(
    draft_type: Literal["pto_manager_request", "peopleops_follow_up", "case_acknowledgement"],
    employee_id: EmployeeId,
    request_start: date | None = None,
    request_end: date | None = None,
    context: Annotated[str | None, Field(default=None, max_length=500)] = None,
) -> HREmailDraftResult:
    """Produce a clearly labelled draft without sending or persisting an email."""
    return draft_hr_email_data(
        draft_type,
        employee_id,
        request_start=request_start,
        request_end=request_end,
        context=context,
    )


@mcp_server.tool(structured_output=True)
def create_mock_hr_ticket(
    category: Literal[
        "workplace_concern", "benefits", "leave", "payroll", "equipment", "onboarding", "other"
    ],
    priority: Literal["low", "normal", "high", "urgent"],
    summary: Annotated[str, Field(min_length=5, max_length=500)],
    affected_employee_id: EmployeeId,
    idempotency_key: IdempotencyKey,
    confirmation_token: Annotated[str, Field(min_length=32, max_length=500)],
) -> MockTicketActionResult:
    """Create an in-memory synthetic ticket only after signed explicit confirmation."""
    return create_mock_hr_ticket_data(
        category,
        priority,
        summary,
        affected_employee_id,
        idempotency_key,
        confirmation_token,
    )
