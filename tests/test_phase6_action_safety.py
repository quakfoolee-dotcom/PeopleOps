from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import peopleops_mcp.actions as actions
from app.mcp_client import sanitize_tool_arguments
from peopleops_mcp.actions import (
    confirm_mock_ticket_action,
    prepare_mock_ticket_action,
    reset_mock_ticket_actions,
)
from peopleops_mcp.tools import create_mock_hr_ticket_data

SUMMARY = "Synthetic workplace concern for controlled review; no finding recorded."
KEY = "request:phase6:ticket-001"


@pytest.fixture(autouse=True)
def reset_actions() -> None:
    reset_mock_ticket_actions()


def _preview():
    return prepare_mock_ticket_action(
        category="workplace_concern",
        priority="high",
        summary=SUMMARY,
        affected_employee_id="E-1011",
        idempotency_key=KEY,
    )


def _create(token: str):
    return create_mock_hr_ticket_data(
        "workplace_concern",
        "high",
        SUMMARY,
        "E-1011",
        KEY,
        token,
    )


def test_mock_ticket_cannot_be_created_without_explicit_confirmation() -> None:
    preview = _preview()

    with pytest.raises(ValueError, match="explicit user confirmation"):
        confirm_mock_ticket_action(preview.confirmation_id, user_confirmed=False)
    with pytest.raises(ValueError, match="malformed"):
        _create(preview.confirmation_id)


def test_confirmed_ticket_creation_is_idempotent_and_in_memory_only() -> None:
    seed_path = Path("mock_data/seed/tickets.json")
    seed_before = seed_path.read_bytes()
    preview = _preview()
    token = confirm_mock_ticket_action(preview.confirmation_id, user_confirmed=True)

    created = _create(token)
    repeated = _create(token)

    assert created.action_status == "created"
    assert created.ticket.ticket_id == "TKT-9001"
    assert created.ticket.confirmation_reference == "CONF-9001"
    assert repeated.action_status == "already_created"
    assert repeated.ticket == created.ticket
    assert created.synthetic_only is True
    assert created.persistence == "in_memory_until_restart"
    assert seed_path.read_bytes() == seed_before


def test_confirmation_token_is_bound_to_preview_and_expiry(monkeypatch) -> None:
    base = datetime(2026, 8, 8, 12, tzinfo=UTC)
    monkeypatch.setattr(actions, "_utc_now", lambda: base)
    preview = _preview()
    token = confirm_mock_ticket_action(preview.confirmation_id, user_confirmed=True)

    with pytest.raises(ValueError, match="does not match"):
        create_mock_hr_ticket_data(
            "workplace_concern",
            "urgent",
            SUMMARY,
            "E-1011",
            KEY,
            token,
        )

    monkeypatch.setattr(actions, "_utc_now", lambda: base + timedelta(hours=1))
    with pytest.raises(ValueError, match="expired"):
        _create(token)


def test_action_trace_arguments_drop_tokens_and_sensitive_free_text() -> None:
    sanitized = sanitize_tool_arguments(
        "create_mock_hr_ticket",
        {
            "category": "workplace_concern",
            "summary": SUMMARY,
            "confirmation_token": "secret-token-value",
            "nested": {"access_token": "also-secret"},
        },
    )

    assert "confirmation_token" not in sanitized
    assert "access_token" not in sanitized["nested"]
    assert sanitized["summary"] == "[redacted: minimum-necessary case summary]"
