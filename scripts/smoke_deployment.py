from __future__ import annotations

import argparse
import json
import sys
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REMOTE_PROMPT = "Can I work remotely from Germany for six weeks?"
EXPECTED_SECTIONS = {"INT-5", "INT-13", "RWK-5", "SEC-8"}
EXPECTED_READY_COMPONENTS = {
    "application",
    "policy_corpus",
    "rag_index",
    "mcp",
    "mock_database",
}


class SmokeFailure(RuntimeError):
    """Raised when a deployment does not satisfy the public release contract."""


class ProviderGenerationUnavailable(SmokeFailure):
    """Raised when a structurally valid response used the verified provider fallback."""


class ProviderAttemptsExhausted(SmokeFailure):
    """Raised when no bounded provider attempt produced an accepted grounded summary."""

    def __init__(self, message: str, attempts: list[dict[str, Any]]) -> None:
        super().__init__(message)
        self.attempts = attempts


def project_version() -> str:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as project_file:
        return str(tomllib.load(project_file)["project"]["version"])


def validate_health(
    payload: dict[str, Any],
    *,
    expected_version: str,
    expected_environment: str | None,
    expected_release_sha: str | None,
    expected_llm_provider: str | None = None,
) -> None:
    if payload.get("status") != "ok":
        raise SmokeFailure(f"health status is {payload.get('status')!r}, expected 'ok'")
    if payload.get("version") != expected_version:
        raise SmokeFailure(
            f"health version is {payload.get('version')!r}, expected {expected_version!r}"
        )
    if expected_environment and payload.get("environment") != expected_environment:
        raise SmokeFailure(
            "health environment is "
            f"{payload.get('environment')!r}, expected {expected_environment!r}"
        )
    if expected_release_sha and payload.get("release_sha") != expected_release_sha:
        raise SmokeFailure(
            f"health release_sha is {payload.get('release_sha')!r}, "
            f"expected {expected_release_sha!r}"
        )

    components = payload.get("components")
    if not isinstance(components, dict):
        raise SmokeFailure("health components are missing")
    unhealthy = {
        name: components.get(name, {}).get("status")
        for name in EXPECTED_READY_COMPONENTS
        if components.get(name, {}).get("status") != "ready"
    }
    if unhealthy:
        raise SmokeFailure(f"required health components are not ready: {unhealthy}")
    if expected_llm_provider:
        provider_status = components.get("llm_provider", {})
        if provider_status.get("status") != "ready":
            raise SmokeFailure(
                "configured LLM provider is not ready: "
                f"{provider_status.get('status')!r}"
            )
        if expected_llm_provider.casefold() not in str(
            provider_status.get("detail", "")
        ).casefold():
            raise SmokeFailure(
                f"health does not identify expected LLM provider {expected_llm_provider!r}"
            )


def validate_chat(
    payload: dict[str, Any], *, expected_llm_provider: str | None = None
) -> None:
    expected_values = {
        "status": "completed",
        "outcome": "conditional",
        "workflow": "remote_work",
    }
    mismatches = {
        key: payload.get(key)
        for key, expected in expected_values.items()
        if payload.get(key) != expected
    }
    if mismatches:
        raise SmokeFailure(f"remote-work response contract mismatch: {mismatches}")

    sections = {
        citation.get("section_id")
        for citation in payload.get("citations", [])
        if isinstance(citation, dict)
    }
    if sections != EXPECTED_SECTIONS:
        raise SmokeFailure(
            f"remote-work citations are {sorted(sections)}, expected {sorted(EXPECTED_SECTIONS)}"
        )

    trace = payload.get("tool_trace")
    if not isinstance(trace, list) or len(trace) != 8:
        raise SmokeFailure("remote-work smoke requires exactly eight traced MCP operations")
    if trace[0].get("tool_name") != "mcp_discover_tools":
        raise SmokeFailure("remote-work trace does not begin with MCP discovery")
    if trace[-1].get("tool_name") != "check_policy_compliance":
        raise SmokeFailure("remote-work trace does not end with policy compliance")

    decision = payload.get("decision_summary")
    if not isinstance(decision, dict):
        raise SmokeFailure("structured decision_summary is missing")
    if decision.get("status_label") != "Conditionally eligible":
        raise SmokeFailure("structured decision status is not conditionally eligible")
    if decision.get("duration_label") != "42 calendar days / 30 business days":
        raise SmokeFailure("structured decision duration is incorrect")
    if decision.get("category_label") != "International exceptional":
        raise SmokeFailure("structured decision category is incorrect")
    if not decision.get("required_approvals") or not decision.get("next_steps"):
        raise SmokeFailure("structured decision approvals or next steps are missing")
    if payload.get("pending_action") is not None:
        raise SmokeFailure("read-only remote-work smoke unexpectedly returned a pending action")
    generation = payload.get("generation")
    if not isinstance(generation, dict):
        raise SmokeFailure("response generation metadata is missing")
    if expected_llm_provider:
        if generation.get("mode") != "provider":
            detail = str(generation.get("detail") or "no fallback detail returned")[:500]
            raise ProviderGenerationUnavailable(
                "configured provider did not generate the grounded summary; "
                f"mode={generation.get('mode')!r}; detail={detail!r}"
            )
        if generation.get("provider") != expected_llm_provider:
            raise SmokeFailure(
                f"response provider is {generation.get('provider')!r}, "
                f"expected {expected_llm_provider!r}"
            )
        if not generation.get("resolved_model"):
            raise SmokeFailure("provider response did not report the resolved model")


def _attempt_evidence(
    payload: dict[str, Any], *, attempt: int, duration_ms: int
) -> dict[str, Any]:
    generation = payload.get("generation")
    if not isinstance(generation, dict):
        generation = {}
    detail = generation.get("detail")
    return {
        "attempt": attempt,
        "duration_ms": duration_ms,
        "request_id": payload.get("request_id"),
        "trace_id": payload.get("trace_id"),
        "mode": generation.get("mode"),
        "provider": generation.get("provider"),
        "model": generation.get("model"),
        "resolved_model": generation.get("resolved_model"),
        "detail": str(detail)[:500] if detail is not None else None,
    }


def run_chat_smoke(
    base_url: str,
    *,
    expected_llm_provider: str | None,
    provider_attempts: int,
) -> tuple[dict[str, Any], int, list[dict[str, Any]]]:
    max_attempts = provider_attempts if expected_llm_provider else 1
    attempts: list[dict[str, Any]] = []
    total_duration_ms = 0
    last_fallback: ProviderGenerationUnavailable | None = None

    for attempt_number in range(1, max_attempts + 1):
        chat, chat_ms = _request(
            base_url,
            "/chat",
            payload={"employee_id": "E-1007", "message": REMOTE_PROMPT},
            timeout_seconds=90,
        )
        total_duration_ms += chat_ms
        if not isinstance(chat, dict):
            raise SmokeFailure("chat endpoint did not return a JSON object")

        evidence = _attempt_evidence(
            chat,
            attempt=attempt_number,
            duration_ms=chat_ms,
        )
        attempts.append(evidence)
        try:
            validate_chat(chat, expected_llm_provider=expected_llm_provider)
        except ProviderGenerationUnavailable as error:
            evidence["result"] = "verified_fallback"
            last_fallback = error
            if attempt_number < max_attempts:
                time.sleep(2)
                continue
            raise ProviderAttemptsExhausted(
                f"provider generation remained unavailable after {max_attempts} "
                f"bounded attempts: {last_fallback}",
                attempts,
            ) from error

        evidence["result"] = "accepted"
        return chat, total_duration_ms, attempts

    raise ProviderAttemptsExhausted(
        f"provider generation did not complete after {max_attempts} bounded attempts",
        attempts,
    )


def _request(
    base_url: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout_seconds: float = 60,
) -> tuple[Any, float]:
    url = urljoin(f"{base_url.rstrip('/')}/", path.lstrip("/"))
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=data,
        method="GET" if payload is None else "POST",
        headers={
            "Accept": "application/json, text/html",
            "Content-Type": "application/json",
            "User-Agent": "PeopleOps-Deployment-Smoke/1.0",
        },
    )
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            body = response.read().decode("utf-8")
            content_type = response.headers.get_content_type()
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        message = f"{request.method} {url} returned HTTP {error.code}: {detail}"
        raise SmokeFailure(message) from error
    except URLError as error:
        raise SmokeFailure(f"{request.method} {url} failed: {error.reason}") from error
    except TimeoutError as error:
        raise SmokeFailure(f"{request.method} {url} timed out") from error
    except OSError as error:
        raise SmokeFailure(f"{request.method} {url} connection failed: {error}") from error
    duration_ms = round((time.perf_counter() - started) * 1000)
    if content_type == "application/json":
        try:
            return json.loads(body), duration_ms
        except json.JSONDecodeError as error:
            raise SmokeFailure(f"{request.method} {url} returned invalid JSON") from error
    return body, duration_ms


def wait_for_health(
    base_url: str,
    *,
    expected_version: str,
    expected_environment: str | None,
    expected_release_sha: str | None,
    expected_llm_provider: str | None,
    deadline_seconds: int,
) -> tuple[dict[str, Any], int, int]:
    started = time.perf_counter()
    deadline = started + deadline_seconds
    attempts = 0
    last_error: Exception | None = None
    while time.perf_counter() < deadline:
        attempts += 1
        try:
            payload, duration_ms = _request(base_url, "/health", timeout_seconds=10)
            if not isinstance(payload, dict):
                raise SmokeFailure("health endpoint did not return a JSON object")
            validate_health(
                payload,
                expected_version=expected_version,
                expected_environment=expected_environment,
                expected_release_sha=expected_release_sha,
                expected_llm_provider=expected_llm_provider,
            )
            wake_ms = round((time.perf_counter() - started) * 1000)
            return payload, duration_ms, wake_ms
        except SmokeFailure as error:
            last_error = error
            time.sleep(2)
    raise SmokeFailure(
        f"deployment did not become ready within {deadline_seconds}s after {attempts} attempts: "
        f"{last_error}"
    )


def run_smoke(args: argparse.Namespace) -> dict[str, Any]:
    expected_version = args.expected_version or project_version()
    health, health_ms, wake_ms = wait_for_health(
        args.base_url,
        expected_version=expected_version,
        expected_environment=args.expected_environment,
        expected_release_sha=args.expected_release_sha,
        expected_llm_provider=args.expected_llm_provider,
        deadline_seconds=args.deadline_seconds,
    )

    root, root_ms = _request(args.base_url, "/")
    if isinstance(root, dict):
        if root.get("name") != "PeopleOps Assistant":
            raise SmokeFailure("root JSON does not identify PeopleOps Assistant")
    elif "PeopleOps Assistant" not in root:
        raise SmokeFailure("root HTML does not identify PeopleOps Assistant")

    chat, chat_ms, provider_attempts = run_chat_smoke(
        args.base_url,
        expected_llm_provider=args.expected_llm_provider,
        provider_attempts=args.provider_attempts,
    )

    return {
        "passed": True,
        "checked_at": datetime.now(UTC).isoformat(),
        "base_url": args.base_url.rstrip("/"),
        "version": health["version"],
        "environment": health["environment"],
        "release_sha": health["release_sha"],
        "cold_start_wait_ms": wake_ms,
        "latency_ms": {"health": health_ms, "root": root_ms, "chat": chat_ms},
        "workflow": {
            "request_id": chat["request_id"],
            "trace_id": chat["trace_id"],
            "citation_sections": sorted(
                citation["section_id"] for citation in chat["citations"]
            ),
            "tool_call_count": len(chat["tool_trace"]),
            "outcome": chat["outcome"],
            "generation": chat["generation"],
            "provider_attempts": provider_attempts,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify startup, release identity, health, root, and a read-only MCP workflow."
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--expected-version")
    parser.add_argument("--expected-environment")
    parser.add_argument("--expected-release-sha")
    parser.add_argument("--expected-llm-provider")
    parser.add_argument("--provider-attempts", type=int, choices=range(1, 6), default=3)
    parser.add_argument("--deadline-seconds", type=int, default=180)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        result = run_smoke(args)
    except Exception as error:
        result = {
            "passed": False,
            "checked_at": datetime.now(UTC).isoformat(),
            "base_url": args.base_url.rstrip("/"),
            "error_type": type(error).__name__,
            "error": str(error),
        }
        if isinstance(error, ProviderAttemptsExhausted):
            result["provider_attempts"] = error.attempts
        rendered = json.dumps(result, indent=2, sort_keys=True)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(f"{rendered}\n", encoding="utf-8")
        print(rendered, file=sys.stderr)
        raise
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(f"{rendered}\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
