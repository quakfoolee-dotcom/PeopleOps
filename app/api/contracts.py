from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.constants import SYNTHETIC_AS_OF_DATE


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class WorkflowStatus(StrEnum):
    COMPLETED = "completed"
    NEEDS_CLARIFICATION = "needs_clarification"
    ESCALATED = "escalated"
    OUT_OF_SCOPE = "out_of_scope"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    ERROR = "error"


class WorkflowOutcome(StrEnum):
    ANSWERED = "answered"
    CONDITIONAL = "conditional"
    DRAFT_ONLY = "draft_only"
    CLARIFICATION_REQUIRED = "clarification_required"
    ESCALATION_REQUIRED = "escalation_required"
    REFUSED = "refused"
    CONFIRMATION_REQUIRED = "confirmation_required"


class WorkflowKind(StrEnum):
    POLICY = "policy"
    REMOTE_WORK = "remote_work"
    PTO = "pto"
    EXPENSE = "expense"
    MOCK_TICKET = "mock_ticket"
    UNSUPPORTED = "unsupported"


class UseCaseHint(StrEnum):
    AUTO = "auto"
    REMOTE_WORK = "remote_work"
    PTO = "pto"
    EXPENSE = "expense"
    BENEFITS_POLICY = "benefits_policy"
    WORKPLACE_CONCERN = "workplace_concern"


class WorkflowStage(StrEnum):
    CLASSIFY = "classify"
    CLARIFY = "clarify"
    DISCOVER = "discover"
    PROFILE = "profile"
    RETRIEVE = "retrieve"
    EVIDENCE = "evidence"
    COMPLIANCE = "compliance"
    DRAFT = "draft"
    CONFIRMATION = "confirmation"
    ACTION = "action"
    ESCALATE = "escalate"
    RESPOND = "respond"


class ToolCallStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    DENIED = "denied"


class Citation(ContractModel):
    policy_id: str = Field(pattern=r"^POL-[A-Z]{3}-\d{3}$")
    section_id: str = Field(pattern=r"^[A-Z]{3}-\d+(?:\.\d+)?$")
    title: str = Field(min_length=1, max_length=200)
    snippet: str = Field(min_length=1, max_length=1000)
    version: str = Field(min_length=1, max_length=40)
    effective_date: date
    source_format: Literal["markdown", "pdf"]
    source_path: str = Field(min_length=1, max_length=500)
    page: int | None = Field(default=None, ge=1)
    chunk_id: str = Field(
        pattern=r"^POL-[A-Z]{3}-\d{3}::[A-Z]{3}-\d+(?:\.\d+)?::\d{2}$"
    )
    retrieval_score: float = Field(ge=0, le=1)


SENSITIVE_TRACE_KEYS = frozenset(
    {
        "authorization",
        "password",
        "secret",
        "token",
        "confirmation_token",
        "api_key",
        "access_token",
    }
)


def _find_sensitive_key(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            normalized_key = str(key).lower()
            if normalized_key in SENSITIVE_TRACE_KEYS:
                return normalized_key
            if nested_match := _find_sensitive_key(nested_value):
                return nested_match
    elif isinstance(value, list):
        for nested_value in value:
            if nested_match := _find_sensitive_key(nested_value):
                return nested_match
    return None


class ToolTraceEntry(ContractModel):
    sequence: int = Field(ge=1)
    tool_name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    sanitized_arguments: dict[str, Any] = Field(default_factory=dict)
    status: ToolCallStatus
    result_summary: str = Field(min_length=1, max_length=1000)
    duration_ms: int = Field(ge=0)
    error_code: str | None = Field(default=None, max_length=100)

    @field_validator("sanitized_arguments")
    @classmethod
    def reject_sensitive_trace_keys(cls, value: dict[str, Any]) -> dict[str, Any]:
        if sensitive_key := _find_sensitive_key(value):
            raise ValueError(f"trace arguments contain sensitive key: {sensitive_key}")
        return value

    @model_validator(mode="after")
    def require_error_code_for_unsuccessful_calls(self) -> "ToolTraceEntry":
        if self.status is ToolCallStatus.SUCCEEDED and self.error_code is not None:
            raise ValueError("successful tool calls cannot carry an error code")
        if self.status is not ToolCallStatus.SUCCEEDED and self.error_code is None:
            raise ValueError("unsuccessful tool calls require an error code")
        return self


class PendingActionPreview(ContractModel):
    action_type: Literal["create_mock_hr_ticket"]
    confirmation_id: str | None = Field(
        default=None,
        pattern=r"^PREVIEW-[A-F0-9]{16}$",
    )
    expires_at: datetime | None = None
    summary: str = Field(min_length=1, max_length=1000)
    sanitized_arguments: dict[str, Any]
    confirmation_required: Literal[True] = True

    @field_validator("sanitized_arguments")
    @classmethod
    def reject_sensitive_preview_keys(cls, value: dict[str, Any]) -> dict[str, Any]:
        if sensitive_key := _find_sensitive_key(value):
            raise ValueError(f"action preview contains sensitive key: {sensitive_key}")
        return value


class DecisionSummary(ContractModel):
    status_label: str = Field(min_length=1, max_length=120)
    duration_label: str | None = Field(default=None, max_length=120)
    category_label: str | None = Field(default=None, max_length=120)
    required_approvals: list[str] = Field(default_factory=list, max_length=12)
    clarification_needed: list[str] = Field(default_factory=list, max_length=8)
    next_steps: list[str] = Field(default_factory=list, min_length=1, max_length=8)


class GenerationMetadata(ContractModel):
    mode: Literal["deterministic", "provider", "deterministic_fallback"] = "deterministic"
    provider: str = Field(default="not-configured", min_length=1, max_length=100)
    model: str = Field(default="not-configured", min_length=1, max_length=200)
    resolved_model: str | None = Field(default=None, max_length=200)
    duration_ms: int = Field(default=0, ge=0)
    detail: str = Field(
        default="Verified deterministic workflow response.",
        min_length=1,
        max_length=500,
    )


class EmailDraft(ContractModel):
    draft_id: str = Field(pattern=r"^DRAFT-[A-F0-9]{12}$")
    draft_type: Literal[
        "pto_manager_request",
        "peopleops_follow_up",
        "case_acknowledgement",
    ]
    employee_id: str = Field(pattern=r"^E-\d{4}$")
    recipient: str = Field(min_length=1, max_length=200)
    label: Literal["Draft - not sent"] = "Draft - not sent"
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=4000)
    sent: Literal[False] = False
    persisted: Literal[False] = False
    warnings: list[str] = Field(default_factory=list, min_length=1, max_length=6)


class AttachmentContext(ContractModel):
    filename: str = Field(
        min_length=1,
        max_length=120,
        pattern=r"^[^/\\\x00-\x1f]+$",
    )
    media_type: Literal["text/plain", "text/markdown", "application/pdf"]
    extracted_text: str = Field(min_length=1, max_length=6000)
    original_size_bytes: int = Field(ge=1, le=2_000_000)
    truncated: bool = False


class AttachmentUploadRequest(ContractModel):
    filename: str = Field(
        min_length=1,
        max_length=120,
        pattern=r"^[^/\\\x00-\x1f]+$",
    )
    media_type: Literal["text/plain", "text/markdown", "application/pdf"]
    content_base64: str = Field(min_length=4, max_length=2_700_000)


class ChatRequest(ContractModel):
    request_id: UUID = Field(default_factory=uuid4)
    message: str = Field(min_length=1, max_length=4000)
    employee_id: str | None = Field(default=None, pattern=r"^E-\d{4}$")
    use_case: UseCaseHint = UseCaseHint.AUTO
    attachment: AttachmentContext | None = None
    as_of_date: date = SYNTHETIC_AS_OF_DATE
    confirmation_token: str | None = Field(default=None, min_length=16, max_length=500)


class ChatResponse(ContractModel):
    request_id: UUID
    trace_id: UUID = Field(default_factory=uuid4)
    as_of_date: date
    status: WorkflowStatus
    outcome: WorkflowOutcome
    answer: str = Field(min_length=1, max_length=12000)
    workflow: WorkflowKind = WorkflowKind.UNSUPPORTED
    workflow_state: WorkflowStage = WorkflowStage.RESPOND
    citations: list[Citation] = Field(default_factory=list)
    tool_trace: list[ToolTraceEntry] = Field(default_factory=list)
    decision_summary: DecisionSummary | None = None
    generation: GenerationMetadata = Field(default_factory=GenerationMetadata)
    email_draft: EmailDraft | None = None
    pending_action: PendingActionPreview | None = None

    @model_validator(mode="after")
    def enforce_confirmation_status(self) -> "ChatResponse":
        waiting = self.status is WorkflowStatus.AWAITING_CONFIRMATION
        if waiting != (self.pending_action is not None):
            raise ValueError(
                "pending_action must be present exactly when status is awaiting_confirmation"
            )
        if waiting and self.outcome is not WorkflowOutcome.CONFIRMATION_REQUIRED:
            raise ValueError("awaiting confirmation requires confirmation_required outcome")
        has_email_draft = self.email_draft is not None
        if has_email_draft != (self.outcome is WorkflowOutcome.DRAFT_ONLY):
            raise ValueError(
                "email_draft must be present exactly when outcome is draft_only"
            )
        if has_email_draft and self.status is not WorkflowStatus.COMPLETED:
            raise ValueError("email drafts require a completed workflow")
        return self


class ConfirmMockTicketRequest(ContractModel):
    confirmation_id: str = Field(pattern=r"^PREVIEW-[A-F0-9]{16}$")
    user_confirmed: Literal[True]


class ConfirmMockTicketResponse(ContractModel):
    confirmation_id: str = Field(pattern=r"^PREVIEW-[A-F0-9]{16}$")
    confirmation_token: str = Field(min_length=32, max_length=500)
    synthetic_only: Literal[True] = True
