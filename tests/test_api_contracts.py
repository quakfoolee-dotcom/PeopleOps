from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.contracts import (
    AttachmentContext,
    ChatRequest,
    ChatResponse,
    Citation,
    ConfirmMockTicketRequest,
    EmailDraft,
    PendingActionPreview,
    ToolCallStatus,
    ToolTraceEntry,
    UseCaseHint,
    WorkflowOutcome,
    WorkflowStatus,
)
from app.core.constants import SYNTHETIC_AS_OF_DATE


def test_chat_request_uses_fixed_as_of_date_and_forbids_extra_fields() -> None:
    request = ChatRequest(message="What is the PTO notice period?", employee_id="E-1001")

    assert request.as_of_date == SYNTHETIC_AS_OF_DATE
    assert request.request_id

    with pytest.raises(ValidationError):
        ChatRequest.model_validate({"message": "Hello", "unexpected": True})


def test_chat_request_accepts_a_bounded_attachment_and_use_case_hint() -> None:
    request = ChatRequest(
        message="What do I need to do?",
        employee_id="E-1007",
        use_case=UseCaseHint.REMOTE_WORK,
        attachment=AttachmentContext(
            filename="travel-details.txt",
            media_type="text/plain",
            extracted_text="Destination: Germany. Duration: six weeks.",
            original_size_bytes=44,
        ),
    )

    assert request.use_case is UseCaseHint.REMOTE_WORK
    assert request.attachment is not None
    assert request.attachment.filename == "travel-details.txt"

    with pytest.raises(ValidationError):
        AttachmentContext(
            filename="../unsafe.txt",
            media_type="text/plain",
            extracted_text="unsafe",
            original_size_bytes=6,
        )


def test_citation_contract_enforces_stable_identifiers() -> None:
    citation = Citation(
        policy_id="POL-PTO-001",
        section_id="PTO-6",
        title="Notice and request process",
        snippet="Three to five scheduled workdays normally require ten business days.",
        version="1.0",
        effective_date=date(2026, 9, 1),
        source_format="markdown",
        source_path="runtime_corpus/POL-PTO-001_Paid-Time-Off-and-Vacation-Policy.md",
        chunk_id="POL-PTO-001::PTO-6::01",
        retrieval_score=0.91,
    )

    assert citation.section_id == "PTO-6"

    with pytest.raises(ValidationError):
        Citation.model_validate({**citation.model_dump(), "policy_id": "invented-policy"})
    with pytest.raises(ValidationError):
        Citation.model_validate({**citation.model_dump(), "retrieval_score": 1.1})


def test_tool_trace_rejects_sensitive_arguments_and_invalid_error_states() -> None:
    successful = ToolTraceEntry(
        sequence=1,
        tool_name="search_policy_documents",
        sanitized_arguments={"query": "PTO notice"},
        status=ToolCallStatus.SUCCEEDED,
        result_summary="Returned section PTO-6.",
        duration_ms=12,
    )
    assert successful.error_code is None

    with pytest.raises(ValidationError, match="sensitive key"):
        ToolTraceEntry(
            sequence=2,
            tool_name="lookup_employee_profile",
            sanitized_arguments={"nested": {"token": "must-not-appear"}},
            status=ToolCallStatus.SUCCEEDED,
            result_summary="Invalid trace.",
            duration_ms=1,
        )

    with pytest.raises(ValidationError, match="require an error code"):
        ToolTraceEntry(
            sequence=2,
            tool_name="lookup_employee_profile",
            sanitized_arguments={"employee_id": "E-9999"},
            status=ToolCallStatus.FAILED,
            result_summary="Employee not found.",
            duration_ms=4,
        )

    with pytest.raises(ValidationError, match="cannot carry an error code"):
        successful.model_copy(update={"error_code": "UNEXPECTED"}).model_validate(
            successful.model_copy(update={"error_code": "UNEXPECTED"}).model_dump()
        )


def test_pending_action_and_response_require_confirmation_together() -> None:
    request_id = uuid4()
    pending_action = PendingActionPreview(
        action_type="create_mock_hr_ticket",
        summary="Preview of a synthetic HR case.",
        sanitized_arguments={"employee_id": "E-1011", "priority": "high"},
    )
    response = ChatResponse(
        request_id=request_id,
        as_of_date=date(2026, 9, 1),
        status=WorkflowStatus.AWAITING_CONFIRMATION,
        outcome=WorkflowOutcome.CONFIRMATION_REQUIRED,
        answer="Review this preview and explicitly confirm before creation.",
        pending_action=pending_action,
    )

    assert response.pending_action is not None
    assert response.trace_id

    with pytest.raises(ValidationError, match="pending_action"):
        ChatResponse(
            request_id=request_id,
            as_of_date=date(2026, 9, 1),
            status=WorkflowStatus.AWAITING_CONFIRMATION,
            outcome=WorkflowOutcome.CONFIRMATION_REQUIRED,
            answer="Missing preview.",
        )

    with pytest.raises(ValidationError, match="confirmation_required"):
        ChatResponse(
            request_id=request_id,
            as_of_date=date(2026, 9, 1),
            status=WorkflowStatus.AWAITING_CONFIRMATION,
            outcome=WorkflowOutcome.ANSWERED,
            answer="Wrong outcome.",
            pending_action=pending_action,
        )


def test_draft_only_response_requires_a_structured_unsent_email_draft() -> None:
    draft = EmailDraft(
        draft_id="DRAFT-ABCDEF012345",
        draft_type="pto_manager_request",
        employee_id="E-1021",
        recipient="Taylor Morgan",
        subject="PTO request: 2026-09-21 to 2026-09-23",
        body="Hi Taylor,\n\nI would like to request PTO.\n\nThank you,\nLogan",
        warnings=["Draft only - no email was sent."],
    )
    response = ChatResponse(
        request_id=uuid4(),
        as_of_date=date(2026, 9, 1),
        status=WorkflowStatus.COMPLETED,
        outcome=WorkflowOutcome.DRAFT_ONLY,
        answer="The PTO balance is sufficient, subject to manager approval.",
        email_draft=draft,
    )

    assert response.email_draft is not None
    assert response.email_draft.sent is False
    assert response.email_draft.persisted is False

    with pytest.raises(ValidationError, match="email_draft"):
        ChatResponse(
            request_id=uuid4(),
            as_of_date=date(2026, 9, 1),
            status=WorkflowStatus.COMPLETED,
            outcome=WorkflowOutcome.DRAFT_ONLY,
            answer="The structured draft is missing.",
        )

    with pytest.raises(ValidationError, match="email_draft"):
        ChatResponse(
            request_id=uuid4(),
            as_of_date=date(2026, 9, 1),
            status=WorkflowStatus.COMPLETED,
            outcome=WorkflowOutcome.CONDITIONAL,
            answer="A draft cannot accompany an ordinary guidance response.",
            email_draft=draft,
        )


def test_action_preview_rejects_sensitive_keys() -> None:
    with pytest.raises(ValidationError, match="sensitive key"):
        PendingActionPreview(
            action_type="create_mock_hr_ticket",
            summary="Unsafe preview.",
            sanitized_arguments={"authorization": "must-not-appear"},
        )


def test_confirmation_request_requires_an_explicit_true_decision() -> None:
    request = ConfirmMockTicketRequest(
        confirmation_id="PREVIEW-ABCDEF0123456789",
        user_confirmed=True,
    )

    assert request.user_confirmed is True
    with pytest.raises(ValidationError):
        ConfirmMockTicketRequest(
            confirmation_id="PREVIEW-ABCDEF0123456789",
            user_confirmed=False,  # type: ignore[arg-type]
        )
