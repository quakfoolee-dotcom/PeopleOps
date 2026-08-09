from __future__ import annotations

from copy import deepcopy
from http.client import RemoteDisconnected

import pytest

from scripts.smoke_deployment import SmokeFailure, _request, validate_chat, validate_health


def health_payload() -> dict[str, object]:
    return {
        "status": "ok",
        "version": "0.7.0",
        "environment": "production",
        "release_sha": "a" * 40,
        "components": {
            name: {"status": "ready"}
            for name in (
                "application",
                "policy_corpus",
                "rag_index",
                "mcp",
                "mock_database",
            )
        },
    }


def chat_payload() -> dict[str, object]:
    tool_names = [
        "mcp_discover_tools",
        "lookup_employee_profile",
        "search_policy_documents",
        "get_policy_section",
        "get_policy_section",
        "get_policy_section",
        "get_policy_section",
        "check_policy_compliance",
    ]
    return {
        "status": "completed",
        "outcome": "conditional",
        "workflow": "remote_work",
        "citations": [
            {"section_id": section_id}
            for section_id in ("INT-5", "INT-13", "RWK-5", "SEC-8")
        ],
        "tool_trace": [{"tool_name": name} for name in tool_names],
        "decision_summary": {
            "status_label": "Conditionally eligible",
            "duration_label": "42 calendar days / 30 business days",
            "category_label": "International exceptional",
            "required_approvals": ["Manager"],
            "next_steps": ["Provide exact dates."],
        },
        "pending_action": None,
    }


def test_health_smoke_contract_accepts_matching_release() -> None:
    validate_health(
        health_payload(),
        expected_version="0.7.0",
        expected_environment="production",
        expected_release_sha="a" * 40,
    )


def test_health_smoke_contract_rejects_wrong_release() -> None:
    with pytest.raises(SmokeFailure, match="release_sha"):
        validate_health(
            health_payload(),
            expected_version="0.7.0",
            expected_environment="production",
            expected_release_sha="b" * 40,
        )


def test_chat_smoke_contract_accepts_grounded_remote_work() -> None:
    validate_chat(chat_payload())


def test_chat_smoke_contract_rejects_citation_drift() -> None:
    payload = deepcopy(chat_payload())
    payload["citations"] = [{"section_id": "INT-5"}]

    with pytest.raises(SmokeFailure, match="citations"):
        validate_chat(payload)


def test_request_translates_transient_disconnect_for_startup_retry(monkeypatch) -> None:
    def disconnect(*_args, **_kwargs):
        raise RemoteDisconnected("service is still starting")

    monkeypatch.setattr("scripts.smoke_deployment.urlopen", disconnect)

    with pytest.raises(SmokeFailure, match="connection failed"):
        _request("http://127.0.0.1:8000", "/health")
