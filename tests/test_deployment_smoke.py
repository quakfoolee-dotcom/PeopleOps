from __future__ import annotations

from copy import deepcopy
from http.client import RemoteDisconnected

import pytest

from scripts.smoke_deployment import (
    ProviderAttemptsExhausted,
    SmokeFailure,
    _request,
    run_chat_smoke,
    validate_chat,
    validate_health,
)


def health_payload() -> dict[str, object]:
    payload: dict[str, object] = {
        "status": "ok",
        "version": "0.8.0",
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
                "llm_provider",
            )
        },
    }
    components = payload["components"]
    assert isinstance(components, dict)
    components["llm_provider"]["detail"] = "deterministic provider is ready"
    return payload


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
        "generation": {
            "mode": "provider",
            "provider": "deterministic",
            "model": "deterministic-grounded-v1",
            "resolved_model": "deterministic-grounded-v1",
            "duration_ms": 0,
        },
    }


def fallback_chat_payload() -> dict[str, object]:
    payload = deepcopy(chat_payload())
    payload["generation"] = {
        "mode": "deterministic_fallback",
        "provider": "openrouter",
        "model": "openrouter/free",
        "resolved_model": None,
        "duration_ms": None,
        "detail": (
            "Provider output was unavailable or rejected by the grounding gate "
            "(ProviderResponseError); the verified workflow response was returned unchanged."
        ),
    }
    return payload


def test_health_smoke_contract_accepts_matching_release() -> None:
    validate_health(
        health_payload(),
        expected_version="0.8.0",
        expected_environment="production",
        expected_release_sha="a" * 40,
        expected_llm_provider="deterministic",
    )


def test_health_smoke_contract_rejects_wrong_release() -> None:
    with pytest.raises(SmokeFailure, match="release_sha"):
        validate_health(
            health_payload(),
            expected_version="0.8.0",
            expected_environment="production",
            expected_release_sha="b" * 40,
        )


def test_chat_smoke_contract_accepts_grounded_remote_work() -> None:
    validate_chat(chat_payload(), expected_llm_provider="deterministic")


def test_chat_smoke_contract_rejects_citation_drift() -> None:
    payload = deepcopy(chat_payload())
    payload["citations"] = [{"section_id": "INT-5"}]

    with pytest.raises(SmokeFailure, match="citations"):
        validate_chat(payload)


def test_chat_smoke_contract_rejects_missing_provider_generation() -> None:
    payload = fallback_chat_payload()

    with pytest.raises(SmokeFailure, match="did not generate"):
        validate_chat(payload, expected_llm_provider="openrouter")


def test_provider_smoke_accepts_success_after_verified_fallback(monkeypatch) -> None:
    responses = [(fallback_chat_payload(), 120), (chat_payload(), 210)]

    def request(*_args, **_kwargs):
        return responses.pop(0)

    monkeypatch.setattr("scripts.smoke_deployment._request", request)
    monkeypatch.setattr("scripts.smoke_deployment.time.sleep", lambda _seconds: None)

    chat, duration_ms, attempts = run_chat_smoke(
        "https://example.test",
        expected_llm_provider="deterministic",
        provider_attempts=3,
    )

    assert chat["generation"]["mode"] == "provider"
    assert duration_ms == 330
    assert [attempt["result"] for attempt in attempts] == [
        "verified_fallback",
        "accepted",
    ]
    assert "ProviderResponseError" in attempts[0]["detail"]
    assert attempts[1]["resolved_model"] == "deterministic-grounded-v1"


def test_provider_smoke_preserves_all_fallback_evidence_when_exhausted(
    monkeypatch,
) -> None:
    request_count = 0

    def request(*_args, **_kwargs):
        nonlocal request_count
        request_count += 1
        return fallback_chat_payload(), 100 + request_count

    monkeypatch.setattr("scripts.smoke_deployment._request", request)
    monkeypatch.setattr("scripts.smoke_deployment.time.sleep", lambda _seconds: None)

    with pytest.raises(ProviderAttemptsExhausted, match="3 bounded attempts") as error:
        run_chat_smoke(
            "https://example.test",
            expected_llm_provider="openrouter",
            provider_attempts=3,
        )

    assert request_count == 3
    assert len(error.value.attempts) == 3
    assert all(
        attempt["result"] == "verified_fallback"
        for attempt in error.value.attempts
    )
    assert [attempt["attempt"] for attempt in error.value.attempts] == [1, 2, 3]


def test_provider_smoke_does_not_retry_structural_contract_failure(monkeypatch) -> None:
    request_count = 0
    invalid = deepcopy(chat_payload())
    invalid["citations"] = [{"section_id": "INT-5"}]

    def request(*_args, **_kwargs):
        nonlocal request_count
        request_count += 1
        return invalid, 100

    monkeypatch.setattr("scripts.smoke_deployment._request", request)

    with pytest.raises(SmokeFailure, match="citations"):
        run_chat_smoke(
            "https://example.test",
            expected_llm_provider="deterministic",
            provider_attempts=3,
        )

    assert request_count == 1


def test_smoke_without_expected_provider_uses_one_request(monkeypatch) -> None:
    request_count = 0
    deterministic = fallback_chat_payload()
    deterministic["generation"] = {
        "mode": "deterministic",
        "provider": "not-configured",
        "detail": "Verified deterministic workflow response.",
    }

    def request(*_args, **_kwargs):
        nonlocal request_count
        request_count += 1
        return deterministic, 75

    monkeypatch.setattr("scripts.smoke_deployment._request", request)

    _, _, attempts = run_chat_smoke(
        "https://example.test",
        expected_llm_provider=None,
        provider_attempts=5,
    )

    assert request_count == 1
    assert attempts[0]["result"] == "accepted"


def test_request_translates_transient_disconnect_for_startup_retry(monkeypatch) -> None:
    def disconnect(*_args, **_kwargs):
        raise RemoteDisconnected("service is still starting")

    monkeypatch.setattr("scripts.smoke_deployment.urlopen", disconnect)

    with pytest.raises(SmokeFailure, match="connection failed"):
        _request("http://127.0.0.1:8000", "/health")
