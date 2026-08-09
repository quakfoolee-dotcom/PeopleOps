from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any

from mcp import Client

from app.api.contracts import (
    SENSITIVE_TRACE_KEYS,
    ToolCallStatus,
    ToolTraceEntry,
)


def _elapsed_ms(started: float) -> int:
    return max(0, round((perf_counter() - started) * 1000))


def sanitize_tool_arguments(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Remove credentials and minimize sensitive free text before recording a trace."""

    def sanitize(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                str(key): sanitize(nested)
                for key, nested in value.items()
                if str(key).casefold() not in SENSITIVE_TRACE_KEYS
            }
        if isinstance(value, list):
            return [sanitize(item) for item in value]
        return value

    sanitized = sanitize(arguments)
    if tool_name == "create_mock_hr_ticket" and "summary" in sanitized:
        sanitized["summary"] = "[redacted: minimum-necessary case summary]"
    if tool_name == "draft_hr_email" and "context" in sanitized:
        sanitized["context"] = "[redacted: draft context]"
    return sanitized


class MCPToolExecutor:
    """Apply one timeout and trace contract to discovery and every MCP invocation."""

    def __init__(self, timeout_seconds: float) -> None:
        self.timeout_seconds = float(timeout_seconds)

    async def discover(
        self,
        client: Client,
        trace: list[ToolTraceEntry],
    ) -> set[str]:
        started = perf_counter()
        try:
            result = await asyncio.wait_for(
                client.list_tools(),
                timeout=self.timeout_seconds,
            )
            tool_names = {tool.name for tool in result.tools}
            trace.append(
                ToolTraceEntry(
                    sequence=len(trace) + 1,
                    tool_name="mcp_discover_tools",
                    sanitized_arguments={},
                    status=ToolCallStatus.SUCCEEDED,
                    result_summary=(
                        f"Discovered {len(tool_names)} tools: "
                        f"{', '.join(sorted(tool_names))}."
                    ),
                    duration_ms=_elapsed_ms(started),
                )
            )
            return tool_names
        except TimeoutError:
            trace.append(
                ToolTraceEntry(
                    sequence=len(trace) + 1,
                    tool_name="mcp_discover_tools",
                    sanitized_arguments={},
                    status=ToolCallStatus.TIMED_OUT,
                    result_summary="MCP tool discovery timed out.",
                    duration_ms=_elapsed_ms(started),
                    error_code="mcp_timeout",
                )
            )
            raise
        except Exception as error:
            trace.append(
                ToolTraceEntry(
                    sequence=len(trace) + 1,
                    tool_name="mcp_discover_tools",
                    sanitized_arguments={},
                    status=ToolCallStatus.FAILED,
                    result_summary="MCP tool discovery failed.",
                    duration_ms=_elapsed_ms(started),
                    error_code=type(error).__name__.casefold(),
                )
            )
            raise

    async def call(
        self,
        client: Client,
        trace: list[ToolTraceEntry],
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        started = perf_counter()
        sanitized = sanitize_tool_arguments(tool_name, arguments)
        try:
            result = await asyncio.wait_for(
                client.call_tool(
                    tool_name,
                    arguments,
                    read_timeout_seconds=self.timeout_seconds,
                ),
                timeout=self.timeout_seconds,
            )
            if result.is_error or result.structured_content is None:
                raise RuntimeError(f"MCP tool {tool_name} returned an error")
            payload = dict(result.structured_content)
            trace.append(
                ToolTraceEntry(
                    sequence=len(trace) + 1,
                    tool_name=tool_name,
                    sanitized_arguments=sanitized,
                    status=ToolCallStatus.SUCCEEDED,
                    result_summary=self._result_summary(tool_name, payload),
                    duration_ms=_elapsed_ms(started),
                )
            )
            return payload
        except TimeoutError:
            trace.append(
                ToolTraceEntry(
                    sequence=len(trace) + 1,
                    tool_name=tool_name,
                    sanitized_arguments=sanitized,
                    status=ToolCallStatus.TIMED_OUT,
                    result_summary=f"{tool_name} timed out.",
                    duration_ms=_elapsed_ms(started),
                    error_code="tool_timeout",
                )
            )
            raise
        except Exception as error:
            trace.append(
                ToolTraceEntry(
                    sequence=len(trace) + 1,
                    tool_name=tool_name,
                    sanitized_arguments=sanitized,
                    status=ToolCallStatus.FAILED,
                    result_summary=f"{tool_name} failed without returning trusted data.",
                    duration_ms=_elapsed_ms(started),
                    error_code=type(error).__name__.casefold(),
                )
            )
            raise

    @staticmethod
    def _result_summary(tool_name: str, payload: dict[str, Any]) -> str:
        if tool_name == "lookup_employee_profile":
            return f"Synthetic employee lookup found={payload.get('found', False)}."
        if tool_name == "search_policy_documents":
            sections = [item["section_id"] for item in payload.get("matches", [])]
            return f"Returned {len(sections)} cited policy chunks: {', '.join(sections)}."
        if tool_name == "get_policy_section":
            return (
                f"Exact section found={payload.get('found', False)} with "
                f"{len(payload.get('evidence', []))} authoritative chunks."
            )
        if tool_name == "check_pto_balance":
            return (
                f"PTO record found={payload.get('found', False)}; "
                f"sufficient_balance={payload.get('sufficient_balance')}."
            )
        if tool_name == "lookup_benefits_status":
            return (
                f"Benefits record found={payload.get('found', False)}; "
                f"enrollment={payload.get('enrollment_status')}."
            )
        if tool_name == "check_policy_compliance":
            return (
                f"Compliance screen status={payload.get('status')}; "
                f"category={payload.get('category')}."
            )
        if tool_name == "draft_hr_email":
            return f"Created {payload.get('label', 'draft')}; sent=false; persisted=false."
        if tool_name == "create_mock_hr_ticket":
            ticket = payload.get("ticket", {})
            return (
                f"Mock action status={payload.get('action_status')}; "
                f"ticket_id={ticket.get('ticket_id')}."
            )
        return "MCP tool returned schema-valid structured content."
