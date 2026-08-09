from __future__ import annotations

import asyncio
import json
from datetime import date

import httpx
import pytest

from app.agent import PeopleOpsOrchestrator
from app.api.contracts import ChatRequest, Citation, DecisionSummary, WorkflowKind
from app.mcp_client import MCPGateway
from app.providers import (
    DeterministicProvider,
    GroundedSynthesisRequest,
    OpenAICompatibleProvider,
    ProviderAuthenticationError,
    ProviderResponseError,
)
from peopleops_mcp.server import mcp_server


def citation(policy_id: str = "POL-INT-001", section_id: str = "INT-5") -> Citation:
    return Citation(
        policy_id=policy_id,
        section_id=section_id,
        title="Synthetic policy section",
        snippet="A 42-day request requires Manager review and is not approval.",
        version="1.0",
        effective_date=date(2026, 9, 1),
        source_format="markdown",
        source_path=f"policy_corpus/runtime_corpus/{policy_id}.md",
        chunk_id=f"{policy_id}::{section_id}::01",
        retrieval_score=1,
    )


def synthesis_request() -> GroundedSynthesisRequest:
    evidence = citation()
    return GroundedSynthesisRequest(
        request_id="00000000-0000-0000-0000-000000000001",
        user_message="Can I work remotely for 42 days?",
        workflow=WorkflowKind.REMOTE_WORK,
        deterministic_answer=(
            "Conditionally eligible for 42 days with Manager review; this is not approval."
        ),
        decision_summary=DecisionSummary(
            status_label="Conditionally eligible",
            duration_label="42 days",
            category_label="International exceptional",
            required_approvals=["Manager"],
            next_steps=["Provide exact dates."],
        ),
        citations=(evidence,),
        protected_facts=("Conditionally eligible", "42 days", "Manager", "not approval"),
    )


def provider(
    transport: httpx.AsyncBaseTransport,
    *,
    timeout_seconds: float = 2,
) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        name="openrouter",
        model="openrouter/free",
        base_url="https://openrouter.ai/api/v1",
        api_key="test-key-never-logged",
        timeout_seconds=timeout_seconds,
        max_output_tokens=500,
        temperature=0,
        health_cache_seconds=60,
        http_referer="https://peopleops-assistant-demo.onrender.com",
        app_title="PeopleOps Assistant",
        transport=transport,
    )


def valid_completion() -> dict[str, object]:
    return {
        "model": "nvidia/example:free",
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "summary": (
                                "Conditionally eligible for 42 days with Manager review; this is "
                                "not approval. [POL-INT-001 § INT-5]"
                            ),
                            "citation_ids": ["POL-INT-001::INT-5::01"],
                        }
                    )
                }
            }
        ],
    }


def test_openrouter_adapter_sends_current_contract_and_validates_grounding() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=valid_completion())

    result = asyncio.run(
        provider(httpx.MockTransport(handler)).synthesize(synthesis_request())
    )

    assert result.provider == "openrouter"
    assert result.configured_model == "openrouter/free"
    assert result.resolved_model == "nvidia/example:free"
    assert result.cited_chunk_ids == ("POL-INT-001::INT-5::01",)
    assert len(requests) == 1
    sent = requests[0]
    assert sent.url.path == "/api/v1/chat/completions"
    assert sent.headers["authorization"] == "Bearer test-key-never-logged"
    assert sent.headers["http-referer"] == "https://peopleops-assistant-demo.onrender.com"
    body = json.loads(sent.content)
    assert body["model"] == "openrouter/free"
    assert body["max_completion_tokens"] == 500
    assert body["response_format"] == {"type": "json_object"}
    assert "hidden reasoning" in body["messages"][0]["content"]


def test_openrouter_adapter_retries_one_transient_failure() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, headers={"Retry-After": "0"})
        return httpx.Response(200, json=valid_completion())

    result = asyncio.run(
        provider(httpx.MockTransport(handler)).synthesize(synthesis_request())
    )

    assert attempts == 2
    assert result.summary.startswith("Conditionally eligible")


def test_openrouter_adapter_rejects_unknown_citations_and_facts() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "test/model",
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "summary": (
                                        "Conditionally eligible for 99 days with Manager review. "
                                        "[POL-PTO-999 § PTO-99]"
                                    ),
                                    "citation_ids": ["POL-PTO-999::PTO-99::01"],
                                }
                            )
                        }
                    }
                ],
            },
        )

    with pytest.raises(ProviderResponseError, match="citations"):
        asyncio.run(provider(httpx.MockTransport(handler)).synthesize(synthesis_request()))


def test_openrouter_health_checks_configured_model_and_caches_result() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"data": {"id": "openrouter/free"}})

    adapter = provider(httpx.MockTransport(handler))
    first = asyncio.run(adapter.health())
    second = asyncio.run(adapter.health())

    assert first.status == second.status == "ready"
    assert requests[0].url.path == "/api/v1/model/openrouter/free"
    assert len(requests) == 1


def test_openai_compatible_health_rejects_missing_configured_model() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"id": "different/model"}]})

    adapter = OpenAICompatibleProvider(
        name="openai-compatible",
        model="expected/model",
        base_url="https://example.test/v1",
        api_key="test-key-never-logged",
        timeout_seconds=2,
        max_output_tokens=500,
        temperature=0,
        health_cache_seconds=60,
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(adapter.health())

    assert result.status == "error"
    assert "expected/model" in result.detail


def test_openrouter_authentication_error_does_not_expose_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    with pytest.raises(ProviderAuthenticationError) as captured:
        asyncio.run(provider(httpx.MockTransport(handler)).synthesize(synthesis_request()))

    assert "test-key-never-logged" not in str(captured.value)


def test_orchestrator_uses_provider_after_verified_workflow() -> None:
    orchestrator = PeopleOpsOrchestrator(
        MCPGateway(target=mcp_server, timeout_seconds=2),
        llm_provider=DeterministicProvider(),
    )

    response = asyncio.run(
        orchestrator.run(
            ChatRequest(
                message="Can I work remotely from Germany for six weeks?",
                employee_id="E-1007",
            )
        )
    )

    assert response.generation.mode == "provider"
    assert response.generation.provider == "deterministic"
    assert response.answer.startswith("AI-generated grounded summary")
    assert "Verified workflow result" in response.answer
    assert "not approval" in response.answer
    assert {item.section_id for item in response.citations} == {
        "INT-5",
        "INT-13",
        "RWK-5",
        "SEC-8",
    }


class FailingProvider(DeterministicProvider):
    name = "failing-test-provider"
    model = "failing-test-model"

    async def synthesize(self, request: GroundedSynthesisRequest):
        raise RuntimeError("synthetic provider outage")


def test_orchestrator_falls_back_to_verified_workflow_on_provider_failure() -> None:
    orchestrator = PeopleOpsOrchestrator(
        MCPGateway(target=mcp_server, timeout_seconds=2),
        llm_provider=FailingProvider(),
    )

    response = asyncio.run(
        orchestrator.run(
            ChatRequest(
                message="Can I work remotely from Germany for six weeks?",
                employee_id="E-1007",
            )
        )
    )

    assert response.generation.mode == "deterministic_fallback"
    assert response.generation.provider == "failing-test-provider"
    assert "AI-generated grounded summary" not in response.answer
    assert "not approval" in response.answer
