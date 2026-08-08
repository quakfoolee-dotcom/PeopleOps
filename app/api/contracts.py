from datetime import date
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
    source_format: Literal["markdown", "pdf"]
    source_path: str = Field(min_length=1, max_length=500)


SENSITIVE_TRACE_KEYS = frozenset(
    {"authorization", "password", "secret", "token", "api_key", "access_token"}
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
    summary: str = Field(min_length=1, max_length=1000)
    sanitized_arguments: dict[str, Any]
    confirmation_required: Literal[True] = True

    @field_validator("sanitized_arguments")
    @classmethod
    def reject_sensitive_preview_keys(cls, value: dict[str, Any]) -> dict[str, Any]:
        if sensitive_key := _find_sensitive_key(value):
            raise ValueError(f"action preview contains sensitive key: {sensitive_key}")
        return value


class ChatRequest(ContractModel):
    request_id: UUID = Field(default_factory=uuid4)
    message: str = Field(min_length=1, max_length=4000)
    employee_id: str | None = Field(default=None, pattern=r"^E-\d{4}$")
    as_of_date: date = SYNTHETIC_AS_OF_DATE
    confirmation_token: str | None = Field(default=None, min_length=16, max_length=200)


class ChatResponse(ContractModel):
    request_id: UUID
    as_of_date: date
    status: WorkflowStatus
    outcome: WorkflowOutcome
    answer: str = Field(min_length=1, max_length=12000)
    citations: list[Citation] = Field(default_factory=list)
    tool_trace: list[ToolTraceEntry] = Field(default_factory=list)
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
        return self
