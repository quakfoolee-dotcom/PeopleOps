from time import perf_counter

from app.api.contracts import (
    ChatRequest,
    ChatResponse,
    Citation,
    ToolCallStatus,
    ToolTraceEntry,
    WorkflowOutcome,
    WorkflowStatus,
)
from app.core.config import get_settings
from app.mcp_client import MCPGateway, MCPToolExecutor
from peopleops_mcp.schemas import EmployeeProfileResult, PolicySearchResult
from peopleops_mcp.server import PHASE6_TOOL_NAMES


def _elapsed_ms(started: float) -> int:
    return max(0, round((perf_counter() - started) * 1000))


def _supports_international_demo(message: str) -> bool:
    normalized = message.casefold()
    has_duration = "six week" in normalized or "6 week" in normalized
    has_work_intent = "work" in normalized or "remote" in normalized
    return "germany" in normalized and has_duration and has_work_intent


class PeopleOpsOrchestrator:
    """Run one typed, bounded international-work workflow through an MCP client only."""

    def __init__(self, gateway: MCPGateway | None = None) -> None:
        self.gateway = gateway or MCPGateway()
        self.timeout_seconds = self.gateway.timeout_seconds
        self.executor = MCPToolExecutor(self.timeout_seconds)

    async def run(self, request: ChatRequest) -> ChatResponse:
        settings = get_settings()
        if request.as_of_date != settings.synthetic_as_of_date:
            return self._response(
                request,
                status=WorkflowStatus.NEEDS_CLARIFICATION,
                outcome=WorkflowOutcome.CLARIFICATION_REQUIRED,
                answer=(
                    "This demonstration uses the fixed synthetic as-of date "
                    f"{settings.synthetic_as_of_date.isoformat()}. Please submit the request "
                    "with that date."
                ),
            )
        if request.employee_id is None:
            return self._response(
                request,
                status=WorkflowStatus.NEEDS_CLARIFICATION,
                outcome=WorkflowOutcome.CLARIFICATION_REQUIRED,
                answer="Please provide a synthetic employee ID in the form E-####.",
            )
        if not _supports_international_demo(request.message):
            return self._response(
                request,
                status=WorkflowStatus.OUT_OF_SCOPE,
                outcome=WorkflowOutcome.REFUSED,
                answer=(
                    "The current bounded workflow supports the international remote-work "
                    "demonstration. "
                    "No policy or employee-data tools were called for this unsupported request."
                ),
            )

        trace: list[ToolTraceEntry] = []
        connection_started = perf_counter()
        try:
            async with self.gateway.connect() as client:
                tool_names = await self.executor.discover(client, trace)
                if not PHASE6_TOOL_NAMES.issubset(tool_names):
                    missing = sorted(PHASE6_TOOL_NAMES - tool_names)
                    trace[-1] = trace[-1].model_copy(
                        update={
                            "status": ToolCallStatus.FAILED,
                            "result_summary": (
                                f"Required MCP tools are missing: {', '.join(missing)}."
                            ),
                            "error_code": "required_tool_missing",
                        }
                    )
                    return self._service_error(request, trace)

                profile_payload = await self.executor.call(
                    client,
                    trace,
                    "lookup_employee_profile",
                    {"employee_id": request.employee_id},
                )
                profile_result = EmployeeProfileResult.model_validate(profile_payload)
                if not profile_result.found or profile_result.profile is None:
                    return self._response(
                        request,
                        status=WorkflowStatus.NEEDS_CLARIFICATION,
                        outcome=WorkflowOutcome.CLARIFICATION_REQUIRED,
                        answer=(
                            f"Synthetic employee {request.employee_id} was not found. "
                            "Check the employee selector and try again."
                        ),
                        tool_trace=trace,
                    )

                policy_payload = await self.executor.call(
                    client,
                    trace,
                    "search_policy_documents",
                    {"query": request.message},
                )
                policy_result = PolicySearchResult.model_validate(policy_payload)
                if not policy_result.sufficient_evidence:
                    return self._response(
                        request,
                        status=WorkflowStatus.ESCALATED,
                        outcome=WorkflowOutcome.ESCALATION_REQUIRED,
                        answer=(
                            "The hybrid policy tool did not return enough evidence to "
                            "answer safely. Escalate to People Operations rather than "
                            "inferring a rule."
                        ),
                        tool_trace=trace,
                    )

                citations = [
                    Citation.model_validate(match.model_dump())
                    for match in policy_result.matches
                ]
                return self._response(
                    request,
                    status=WorkflowStatus.COMPLETED,
                    outcome=WorkflowOutcome.CONDITIONAL,
                    answer=self._international_remote_answer(profile_result),
                    citations=citations,
                    tool_trace=trace,
                )
        except TimeoutError:
            if not trace or trace[-1].status is ToolCallStatus.SUCCEEDED:
                trace.append(
                    ToolTraceEntry(
                        sequence=len(trace) + 1,
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
            return self._service_error(request, trace)
        except Exception as error:
            if not trace or trace[-1].status is ToolCallStatus.SUCCEEDED:
                failed_step = "mcp_discover_tools" if not trace else "mcp_response_validation"
                trace.append(
                    ToolTraceEntry(
                        sequence=len(trace) + 1,
                        tool_name=failed_step,
                        sanitized_arguments={},
                        status=ToolCallStatus.FAILED,
                        result_summary="The MCP service could not complete the bounded workflow.",
                        duration_ms=_elapsed_ms(connection_started),
                        error_code=type(error).__name__.casefold(),
                    )
                )
            return self._service_error(request, trace)

    @staticmethod
    def _international_remote_answer(profile_result: EmployeeProfileResult) -> str:
        profile = profile_result.profile
        assert profile is not None
        location = profile.home_office
        return (
            "Conditional guidance - this request is not automatically approved. "
            f"{profile.synthetic_name} ({profile.employee_id}) is an active "
            f"{profile.employment_type} {profile.role} with a {profile.remote_work_classification} "
            f"designation and a registered home office in {location.city}, "
            f"{location.province_or_state}, {location.country_code}. A six-week Germany request "
            "normally represents about 30 business days and falls in the International exceptional "
            "category. Submit a complete request at least 30 business days in advance. The normal "
            "decision path requires manager, director, People Operations, Security, Finance/Tax, "
            "VP sponsor, and Legal review. The employee must also demonstrate a lawful basis to "
            "work, meet security and time-zone controls, and remain within cumulative limits. Do "
            "not work "
            "from Germany until the location and dates are expressly approved."
        )

    @staticmethod
    def _response(
        request: ChatRequest,
        *,
        status: WorkflowStatus,
        outcome: WorkflowOutcome,
        answer: str,
        citations: list[Citation] | None = None,
        tool_trace: list[ToolTraceEntry] | None = None,
    ) -> ChatResponse:
        return ChatResponse(
            request_id=request.request_id,
            as_of_date=request.as_of_date,
            status=status,
            outcome=outcome,
            answer=answer,
            citations=citations or [],
            tool_trace=tool_trace or [],
        )

    def _service_error(
        self,
        request: ChatRequest,
        trace: list[ToolTraceEntry],
    ) -> ChatResponse:
        return self._response(
            request,
            status=WorkflowStatus.ERROR,
            outcome=WorkflowOutcome.ESCALATION_REQUIRED,
            answer=(
                "The MCP service is unavailable or incomplete, so PeopleOps Assistant did not "
                "infer an answer. Try again or escalate to People Operations."
            ),
            tool_trace=trace,
        )
