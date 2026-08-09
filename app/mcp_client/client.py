from contextlib import AbstractAsyncContextManager
from typing import Any

from mcp import Client

from app.core.config import get_settings


class MCPGateway:
    """Create official MCP client sessions without exposing data stores to the agent."""

    def __init__(self, target: Any | None = None, timeout_seconds: float | None = None) -> None:
        settings = get_settings()
        self.target = target if target is not None else settings.mcp_server_url
        self.timeout_seconds = (
            float(timeout_seconds)
            if timeout_seconds is not None
            else float(settings.tool_timeout_seconds)
        )

    def connect(self) -> AbstractAsyncContextManager[Client]:
        return Client(
            self.target,
            read_timeout_seconds=self.timeout_seconds,
            raise_exceptions=False,
        )
