# MCP client package

This boundary owns official MCP sessions plus shared discovery, invocation, timeout handling,
argument sanitization, bounded result summaries, and operational trace capture for all eight tools.
Phase 7 adds workflow-level retries. The orchestrator must not bypass this package to access policy,
employee data, or mock actions directly.
