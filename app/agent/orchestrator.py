from __future__ import annotations

from decimal import Decimal
from time import perf_counter
from typing import Any

from app.agent.workflows import (
    ExpenseIntent,
    PTOIntent,
    RemoteWorkIntent,
    TicketActionCoordinator,
    TicketIntent,
    UnsupportedIntent,
    WorkflowIntent,
    WorkflowMachine,
    classify_request,
)
from app.api.contracts import (
    ChatRequest,
    ChatResponse,
    Citation,
    PendingActionPreview,
    ToolCallStatus,
    ToolTraceEntry,
    WorkflowKind,
    WorkflowOutcome,
    WorkflowStage,
    WorkflowStatus,
)
from app.core.config import get_settings
from app.mcp_client import MCPGateway, MCPToolExecutor
from peopleops_mcp.schemas import (
    ComplianceCheckResult,
    EmployeeProfileResult,
    HREmailDraftResult,
    MockTicketActionResult,
    PolicySearchResult,
    PolicySectionResult,
    PTOBalanceResult,
)

REMOTE_SECTIONS = (
    ("POL-INT-001", "INT-5"),
    ("POL-INT-001", "INT-13"),
    ("POL-RWK-001", "RWK-5"),
    ("POL-SEC-001", "SEC-8"),
)
PTO_SECTIONS = (
    ("POL-PTO-001", "PTO-6"),
    ("POL-PTO-001", "PTO-7"),
)
EXPENSE_SECTIONS = (
    ("POL-EQP-001", "EQP-4"),
    ("POL-EXP-001", "EXP-3"),
    ("POL-EXP-001", "EXP-7"),
)
TICKET_SECTIONS = (
    ("POL-CON-001", "CON-11"),
    ("POL-HRC-001", "HRC-6"),
    ("POL-HRC-001", "HRC-8"),
)

REQUIRED_TOOLS = {
    WorkflowKind.REMOTE_WORK: frozenset(
        {
            "lookup_employee_profile",
            "search_policy_documents",
            "get_policy_section",
            "check_policy_compliance",
        }
    ),
    WorkflowKind.PTO: frozenset(
        {
            "lookup_employee_profile",
            "check_pto_balance",
            "search_policy_documents",
            "get_policy_section",
            "check_policy_compliance",
            "draft_hr_email",
        }
    ),
    WorkflowKind.EXPENSE: frozenset(
        {
            "lookup_employee_profile",
            "search_policy_documents",
            "get_policy_section",
            "check_policy_compliance",
        }
    ),
    WorkflowKind.MOCK_TICKET: frozenset(
        {
            "lookup_employee_profile",
            "search_policy_documents",
            "get_policy_section",
            "create_mock_hr_ticket",
        }
    ),
}


class EvidenceGateError(RuntimeError):
    pass


class PolicyConflictError(RuntimeError):
    pass


class ToolAvailabilityError(RuntimeError):
    pass


def _find_evidence_gate(error: BaseException) -> EvidenceGateError | PolicyConflictError | None:
    if isinstance(error, (EvidenceGateError, PolicyConflictError)):
        return error
    if isinstance(error, BaseExceptionGroup):
        for nested in error.exceptions:
            if gate := _find_evidence_gate(nested):
                return gate
    return None


def _elapsed_ms(started: float) -> int:
    return max(0, round((perf_counter() - started) * 1000))


def _money(value: Decimal | None) -> str:
    return f"{value:.2f}" if value is not None else "unknown"


class PeopleOpsOrchestrator:
    """Run deterministic typed PeopleOps workflows through MCP-only data access."""

    def __init__(
        self,
        gateway: MCPGateway | None = None,
        *,
        ticket_actions: TicketActionCoordinator | None = None,
    ) -> None:
        self.gateway = gateway or MCPGateway()
        self.timeout_seconds = self.gateway.timeout_seconds
        self.executor = MCPToolExecutor(self.timeout_seconds)
        self.ticket_actions = ticket_actions

    async def run(self, request: ChatRequest) -> ChatResponse:
        settings = get_settings()
        intent = classify_request(request.message, request.employee_id)
        machine = WorkflowMachine(intent.kind, max_tool_calls=settings.max_tool_calls)

        if request.as_of_date != settings.synthetic_as_of_date:
            machine.transition(WorkflowStage.CLARIFY)
            return self._finish(
                request,
                machine,
                status=WorkflowStatus.NEEDS_CLARIFICATION,
                outcome=WorkflowOutcome.CLARIFICATION_REQUIRED,
                answer=(
                    "This demonstration uses the fixed synthetic as-of date "
                    f"{settings.synthetic_as_of_date.isoformat()}. Please submit the request "
                    "with that date."
                ),
            )

        if intent.clarification_needed:
            machine.transition(WorkflowStage.CLARIFY)
            return self._finish(
                request,
                machine,
                status=WorkflowStatus.NEEDS_CLARIFICATION,
                outcome=WorkflowOutcome.CLARIFICATION_REQUIRED,
                answer=self._clarification_answer(intent),
            )

        if request.confirmation_token is not None and not isinstance(intent, TicketIntent):
            machine.transition(WorkflowStage.RESPOND)
            return self._response(
                request,
                machine,
                status=WorkflowStatus.OUT_OF_SCOPE,
                outcome=WorkflowOutcome.REFUSED,
                answer=(
                    "Confirmation proof is accepted only for the unchanged mock-ticket request "
                    "that produced its preview. No tool was called and no action was performed."
                ),
            )

        if isinstance(intent, UnsupportedIntent):
            machine.transition(WorkflowStage.RESPOND)
            return self._response(
                request,
                machine,
                status=WorkflowStatus.OUT_OF_SCOPE,
                outcome=WorkflowOutcome.REFUSED,
                answer=(
                    f"I cannot complete that request because {intent.reason}. "
                    "I can provide bounded guidance for the supported PeopleOps workflows or "
                    "route you to People Operations."
                ),
            )

        trace: list[ToolTraceEntry] = []
        connection_started = perf_counter()
        try:
            machine.transition(WorkflowStage.DISCOVER)
            async with self.gateway.connect() as client:
                tool_names = await self.executor.discover_with_retry(client, trace)
                required = REQUIRED_TOOLS[intent.kind]
                if missing := sorted(required - tool_names):
                    trace[-1] = trace[-1].model_copy(
                        update={
                            "status": ToolCallStatus.FAILED,
                            "result_summary": (
                                "Required workflow tools are missing: " + ", ".join(missing) + "."
                            ),
                            "error_code": "required_tool_missing",
                        }
                    )
                    raise ToolAvailabilityError(
                        f"required workflow tools are unavailable: {', '.join(missing)}"
                    )

                machine.transition(WorkflowStage.PROFILE)
                profile = await self._profile(client, trace, machine, intent.employee_id)
                if not profile.found or profile.profile is None:
                    machine.transition(WorkflowStage.CLARIFY)
                    return self._finish(
                        request,
                        machine,
                        status=WorkflowStatus.NEEDS_CLARIFICATION,
                        outcome=WorkflowOutcome.CLARIFICATION_REQUIRED,
                        answer=(
                            f"Synthetic employee {intent.employee_id} was not found. "
                            "Check the employee selector and try again."
                        ),
                        tool_trace=trace,
                    )

                if isinstance(intent, RemoteWorkIntent):
                    return await self._run_remote(
                        request, intent, profile, client, trace, machine
                    )
                if isinstance(intent, PTOIntent):
                    return await self._run_pto(request, intent, profile, client, trace, machine)
                if isinstance(intent, ExpenseIntent):
                    return await self._run_expense(
                        request, intent, profile, client, trace, machine
                    )
                if isinstance(intent, TicketIntent):
                    return await self._run_ticket(
                        request, intent, client, trace, machine
                    )
                raise RuntimeError("unsupported typed workflow intent")
        except (EvidenceGateError, PolicyConflictError) as error:
            return self._escalation_response(request, machine, trace, str(error))
        except ToolAvailabilityError:
            return self._service_error(request, machine, trace)
        except TimeoutError:
            if not trace:
                trace.append(
                    ToolTraceEntry(
                        sequence=1,
                        tool_name="mcp_discover_tools",
                        sanitized_arguments={},
                        status=ToolCallStatus.TIMED_OUT,
                        result_summary=(
                            "The MCP service did not respond within the configured timeout."
                        ),
                        duration_ms=_elapsed_ms(connection_started),
                        error_code="mcp_timeout",
                    )
                )
            return self._service_error(request, machine, trace)
        except Exception as error:
            if gate := _find_evidence_gate(error):
                return self._escalation_response(request, machine, trace, str(gate))
            if not trace:
                trace.append(
                    ToolTraceEntry(
                        sequence=1,
                        tool_name="mcp_discover_tools",
                        sanitized_arguments={},
                        status=ToolCallStatus.FAILED,
                        result_summary="The MCP service could not start the bounded workflow.",
                        duration_ms=_elapsed_ms(connection_started),
                        error_code=type(error).__name__.casefold(),
                    )
                )
            return self._service_error(request, machine, trace)

    async def _profile(
        self,
        client: Any,
        trace: list[ToolTraceEntry],
        machine: WorkflowMachine,
        employee_id: str | None,
    ) -> EmployeeProfileResult:
        assert employee_id is not None
        payload = await self._call(
            client,
            trace,
            machine,
            "lookup_employee_profile",
            {"employee_id": employee_id},
        )
        return EmployeeProfileResult.model_validate(payload)

    async def _collect_evidence(
        self,
        client: Any,
        trace: list[ToolTraceEntry],
        machine: WorkflowMachine,
        query: str,
        required_sections: tuple[tuple[str, str], ...],
    ) -> list[Citation]:
        machine.transition(WorkflowStage.RETRIEVE)
        search_payload = await self._call(
            client,
            trace,
            machine,
            "search_policy_documents",
            {"query": query},
        )
        search = PolicySearchResult.model_validate(search_payload)
        if search.conflicts:
            raise PolicyConflictError(
                "Conflicting policy evidence was detected, so the workflow stopped for "
                "People Operations review."
            )
        if not search.sufficient_evidence:
            missing = ", ".join(search.missing_policy_ids) or "required policy evidence"
            raise EvidenceGateError(
                f"Evidence was insufficient ({missing}); no policy conclusion was inferred."
            )

        citations: dict[str, Citation] = {}
        for policy_id, section_id in required_sections:
            section_payload = await self._call(
                client,
                trace,
                machine,
                "get_policy_section",
                {"policy_id": policy_id, "section_id": section_id},
            )
            section = PolicySectionResult.model_validate(section_payload)
            if section.conflicts:
                raise PolicyConflictError(
                    f"Conflicting versions were found for {policy_id} {section_id}; "
                    "the workflow stopped for review."
                )
            if not section.found:
                raise EvidenceGateError(
                    f"Required policy section {policy_id} {section_id} was unavailable; "
                    "no policy conclusion was inferred."
                )
            for evidence in section.evidence:
                citation = Citation.model_validate(evidence.model_dump())
                citations[citation.chunk_id] = citation
        machine.transition(WorkflowStage.EVIDENCE)
        return list(citations.values())

    async def _run_remote(
        self,
        request: ChatRequest,
        intent: RemoteWorkIntent,
        profile: EmployeeProfileResult,
        client: Any,
        trace: list[ToolTraceEntry],
        machine: WorkflowMachine,
    ) -> ChatResponse:
        citations = await self._collect_evidence(
            client, trace, machine, request.message, REMOTE_SECTIONS
        )
        machine.transition(WorkflowStage.COMPLIANCE)
        compliance_payload = await self._call(
            client,
            trace,
            machine,
            "check_policy_compliance",
            {
                "workflow": "international_remote_work",
                "employee_id": intent.employee_id,
                "destination_country_code": intent.destination_country_code,
                "duration_business_days": intent.duration_business_days,
            },
        )
        compliance = ComplianceCheckResult.model_validate(compliance_payload)
        if compliance.status == "needs_clarification":
            machine.transition(WorkflowStage.CLARIFY)
            return self._finish(
                request,
                machine,
                status=WorkflowStatus.NEEDS_CLARIFICATION,
                outcome=WorkflowOutcome.CLARIFICATION_REQUIRED,
                answer=(
                    "The compliance screen needs: "
                    + ", ".join(compliance.clarification_needed)
                    + ". No destination risk or eligibility result was inferred."
                ),
                citations=citations,
                tool_trace=trace,
            )

        employee = profile.profile
        assert employee is not None
        approvals = ", ".join(compliance.required_approvals) or "People Operations review"
        conditions = " ".join(compliance.conditions)
        if compliance.status == "not_eligible":
            answer = (
                f"The bounded screen found this request not eligible under category "
                f"{compliance.category}. {conditions} This is policy guidance, not a legal or "
                "immigration determination."
            )
            outcome = WorkflowOutcome.ANSWERED
        else:
            answer = (
                "Conditionally eligible - this is not approval to work from the destination. "
                f"{employee.synthetic_name} ({employee.employee_id}) is an active "
                f"{employee.employment_type} employee with a "
                f"{employee.remote_work_classification} designation. The "
                f"{intent.duration_business_days}-business-day {intent.destination_name} request "
                f"is classified as {compliance.category}. Required reviews: {approvals}. "
                f"{conditions} Provide exact travel and working dates before final review."
            )
            outcome = WorkflowOutcome.CONDITIONAL
        return self._finish(
            request,
            machine,
            status=WorkflowStatus.COMPLETED,
            outcome=outcome,
            answer=answer,
            citations=citations,
            tool_trace=trace,
        )

    async def _run_pto(
        self,
        request: ChatRequest,
        intent: PTOIntent,
        profile: EmployeeProfileResult,
        client: Any,
        trace: list[ToolTraceEntry],
        machine: WorkflowMachine,
    ) -> ChatResponse:
        assert intent.request_start is not None and intent.request_end is not None
        balance_payload = await self._call(
            client,
            trace,
            machine,
            "check_pto_balance",
            {
                "employee_id": intent.employee_id,
                "request_start": intent.request_start.isoformat(),
                "request_end": intent.request_end.isoformat(),
            },
        )
        balance = PTOBalanceResult.model_validate(balance_payload)
        if not balance.found:
            raise EvidenceGateError(
                "No synthetic PTO balance was available, so eligibility was not inferred."
            )
        citations = await self._collect_evidence(
            client, trace, machine, request.message, PTO_SECTIONS
        )
        machine.transition(WorkflowStage.COMPLIANCE)
        compliance_payload = await self._call(
            client,
            trace,
            machine,
            "check_policy_compliance",
            {
                "workflow": "pto_request",
                "employee_id": intent.employee_id,
                "request_start": intent.request_start.isoformat(),
                "request_end": intent.request_end.isoformat(),
            },
        )
        compliance = ComplianceCheckResult.model_validate(compliance_payload)
        if compliance.status == "needs_clarification":
            machine.transition(WorkflowStage.CLARIFY)
            return self._finish(
                request,
                machine,
                status=WorkflowStatus.NEEDS_CLARIFICATION,
                outcome=WorkflowOutcome.CLARIFICATION_REQUIRED,
                answer="The PTO compliance screen requires exact start and end dates.",
                citations=citations,
                tool_trace=trace,
            )

        employee = profile.profile
        assert employee is not None
        notice = compliance.calculation.normal_notice_business_days
        answer = (
            f"{employee.synthetic_name}'s request covers {balance.requested_workdays} scheduled "
            f"workdays ({_money(balance.requested_hours)} hours). The read-only synthetic balance "
            f"shows {_money(balance.available_hours)} available hours and "
            f"{_money(balance.pending_hours)} pending hours, leaving "
            f"{_money(balance.projected_hours_after_request)} projected hours. Balance sufficient: "
            f"{'yes' if balance.sufficient_balance else 'no'}. Normal notice is {notice} business "
            "days. A sufficient balance does not guarantee approval; the manager must assess "
            "coverage and scheduling. No PTO record was changed."
        )
        outcome = WorkflowOutcome.CONDITIONAL
        if intent.wants_draft:
            machine.transition(WorkflowStage.DRAFT)
            draft_payload = await self._call(
                client,
                trace,
                machine,
                "draft_hr_email",
                {
                    "draft_type": "pto_manager_request",
                    "employee_id": intent.employee_id,
                    "request_start": intent.request_start.isoformat(),
                    "request_end": intent.request_end.isoformat(),
                },
            )
            draft = HREmailDraftResult.model_validate(draft_payload)
            answer += (
                f"\n\n{draft.label}\nSubject: {draft.subject}\n\n{draft.body}\n\n"
                "The draft was not sent or persisted."
            )
            outcome = WorkflowOutcome.DRAFT_ONLY
        return self._finish(
            request,
            machine,
            status=WorkflowStatus.COMPLETED,
            outcome=outcome,
            answer=answer,
            citations=citations,
            tool_trace=trace,
        )

    async def _run_expense(
        self,
        request: ChatRequest,
        intent: ExpenseIntent,
        profile: EmployeeProfileResult,
        client: Any,
        trace: list[ToolTraceEntry],
        machine: WorkflowMachine,
    ) -> ChatResponse:
        assert intent.amount is not None and intent.currency is not None
        citations = await self._collect_evidence(
            client, trace, machine, request.message, EXPENSE_SECTIONS
        )
        machine.transition(WorkflowStage.COMPLIANCE)
        compliance_payload = await self._call(
            client,
            trace,
            machine,
            "check_policy_compliance",
            {
                "workflow": "home_office_expense",
                "employee_id": intent.employee_id,
                "expense_amount": str(intent.amount),
                "currency": intent.currency,
            },
        )
        compliance = ComplianceCheckResult.model_validate(compliance_payload)
        calculation = compliance.calculation
        employee = profile.profile
        assert employee is not None
        if compliance.status == "not_eligible":
            answer = (
                f"{employee.synthetic_name} is not eligible under the ordinary home-office "
                "equipment screen. No reimbursement or preapproval was created."
            )
            outcome = WorkflowOutcome.ANSWERED
        else:
            answer = (
                f"Conditionally eligible - this is not reimbursement or approval. For the "
                f"{intent.currency} {_money(intent.amount)} {intent.item}, the ordinary cap is "
                f"{intent.currency} {_money(calculation.ordinary_reimbursement_cap)} and the "
                f"ordinary employee-paid remainder is {intent.currency} "
                f"{_money(calculation.employee_paid_remainder)}. Required approval: "
                f"{', '.join(compliance.required_approvals)}. Preapproval is required before "
                "purchase. An approved accommodation is a separate exception and was not inferred."
            )
            outcome = WorkflowOutcome.CONDITIONAL
        return self._finish(
            request,
            machine,
            status=WorkflowStatus.COMPLETED,
            outcome=outcome,
            answer=answer,
            citations=citations,
            tool_trace=trace,
        )

    async def _run_ticket(
        self,
        request: ChatRequest,
        intent: TicketIntent,
        client: Any,
        trace: list[ToolTraceEntry],
        machine: WorkflowMachine,
    ) -> ChatResponse:
        citations = await self._collect_evidence(
            client, trace, machine, request.message, TICKET_SECTIONS
        )
        assert intent.employee_id is not None
        idempotency_key = f"phase7:{request.request_id}"
        action_arguments = {
            "category": intent.category,
            "priority": intent.priority,
            "summary": intent.summary,
            "affected_employee_id": intent.employee_id,
            "idempotency_key": idempotency_key,
        }
        if request.confirmation_token is None:
            if self.ticket_actions is None:
                raise RuntimeError("ticket confirmation coordinator is unavailable")
            machine.transition(WorkflowStage.CONFIRMATION)
            started = perf_counter()
            preview = self.ticket_actions.prepare(**action_arguments)
            trace.append(
                ToolTraceEntry(
                    sequence=len(trace) + 1,
                    tool_name="prepare_mock_ticket_preview",
                    sanitized_arguments={
                        "category": preview.category,
                        "priority": preview.priority,
                        "affected_employee_id": preview.affected_employee_id,
                        "routing_team": preview.routing_team,
                        "idempotency_key": preview.idempotency_key,
                        "summary": "[redacted: minimum-necessary case summary]",
                    },
                    status=ToolCallStatus.SUCCEEDED,
                    result_summary=(
                        "Prepared a synthetic action preview; no ticket was created."
                    ),
                    duration_ms=_elapsed_ms(started),
                )
            )
            pending = PendingActionPreview(
                action_type="create_mock_hr_ticket",
                confirmation_id=preview.confirmation_id,
                expires_at=preview.expires_at,
                summary=preview.summary,
                sanitized_arguments={
                    "category": preview.category,
                    "priority": preview.priority,
                    "affected_employee_id": preview.affected_employee_id,
                    "routing_team": preview.routing_team,
                    "idempotency_key": preview.idempotency_key,
                },
            )
            return self._finish(
                request,
                machine,
                status=WorkflowStatus.AWAITING_CONFIRMATION,
                outcome=WorkflowOutcome.CONFIRMATION_REQUIRED,
                answer=(
                    "Review the sanitized mock ticket preview and explicitly confirm it. "
                    "No ticket has been created, and the report is not a finding."
                ),
                citations=citations,
                tool_trace=trace,
                pending_action=pending,
            )

        machine.transition(WorkflowStage.ACTION)
        action_payload = await self._call(
            client,
            trace,
            machine,
            "create_mock_hr_ticket",
            {**action_arguments, "confirmation_token": request.confirmation_token},
        )
        action = MockTicketActionResult.model_validate(action_payload)
        return self._finish(
            request,
            machine,
            status=WorkflowStatus.COMPLETED,
            outcome=WorkflowOutcome.ANSWERED,
            answer=(
                f"Synthetic mock ticket {action.ticket.ticket_id} was "
                f"{action.action_status.replace('_', ' ')} and routed to "
                f"{action.ticket.routing_team}. It exists only in memory for this demonstration; "
                "no production HR system was updated."
            ),
            citations=citations,
            tool_trace=trace,
        )

    async def _call(
        self,
        client: Any,
        trace: list[ToolTraceEntry],
        machine: WorkflowMachine,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        machine.reserve_tool_call()
        return await self.executor.call_with_retry(
            client,
            trace,
            tool_name,
            arguments,
            max_attempts=2,
        )

    @staticmethod
    def _clarification_answer(intent: WorkflowIntent) -> str:
        missing = ", ".join(intent.clarification_needed)
        if intent.kind is WorkflowKind.PTO:
            return (
                f"Please provide {missing}. Use exact calendar dates; PeopleOps Assistant will "
                "not silently resolve relative phrases such as 'next week' or invent a balance."
            )
        if intent.kind is WorkflowKind.REMOTE_WORK:
            return (
                f"Please provide {missing}. Destination and duration determine the review path, "
                "so no international-work category was selected."
            )
        if intent.kind is WorkflowKind.EXPENSE:
            return f"Please provide {missing}; no allowance or reimbursement was inferred."
        if intent.kind is WorkflowKind.MOCK_TICKET:
            return f"Please provide {missing} before a sanitized ticket preview can be prepared."
        return f"Please provide {missing}."

    def _escalation_response(
        self,
        request: ChatRequest,
        machine: WorkflowMachine,
        trace: list[ToolTraceEntry],
        reason: str,
    ) -> ChatResponse:
        if machine.stage is not WorkflowStage.ESCALATE:
            machine.transition(WorkflowStage.ESCALATE)
        return self._finish(
            request,
            machine,
            status=WorkflowStatus.ESCALATED,
            outcome=WorkflowOutcome.ESCALATION_REQUIRED,
            answer=f"{reason} Escalate to People Operations rather than guessing.",
            tool_trace=trace,
        )

    def _service_error(
        self,
        request: ChatRequest,
        machine: WorkflowMachine,
        trace: list[ToolTraceEntry],
    ) -> ChatResponse:
        if machine.stage is not WorkflowStage.ESCALATE:
            machine.transition(WorkflowStage.ESCALATE)
        return self._finish(
            request,
            machine,
            status=WorkflowStatus.ERROR,
            outcome=WorkflowOutcome.ESCALATION_REQUIRED,
            answer=(
                "The required MCP service or workflow tool remained unavailable after one "
                "bounded retry. PeopleOps Assistant did not infer an answer or perform an action. "
                "Try again or escalate to People Operations."
            ),
            tool_trace=trace,
        )

    def _finish(
        self,
        request: ChatRequest,
        machine: WorkflowMachine,
        *,
        status: WorkflowStatus,
        outcome: WorkflowOutcome,
        answer: str,
        citations: list[Citation] | None = None,
        tool_trace: list[ToolTraceEntry] | None = None,
        pending_action: PendingActionPreview | None = None,
    ) -> ChatResponse:
        if machine.stage is not WorkflowStage.RESPOND:
            machine.transition(WorkflowStage.RESPOND)
        return self._response(
            request,
            machine,
            status=status,
            outcome=outcome,
            answer=answer,
            citations=citations,
            tool_trace=tool_trace,
            pending_action=pending_action,
        )

    @staticmethod
    def _response(
        request: ChatRequest,
        machine: WorkflowMachine,
        *,
        status: WorkflowStatus,
        outcome: WorkflowOutcome,
        answer: str,
        citations: list[Citation] | None = None,
        tool_trace: list[ToolTraceEntry] | None = None,
        pending_action: PendingActionPreview | None = None,
    ) -> ChatResponse:
        return ChatResponse(
            request_id=request.request_id,
            as_of_date=request.as_of_date,
            status=status,
            outcome=outcome,
            answer=answer,
            workflow=machine.kind,
            workflow_state=machine.stage,
            citations=citations or [],
            tool_trace=tool_trace or [],
            pending_action=pending_action,
        )
