# MCP client package

This boundary owns official MCP sessions plus shared discovery, invocation, timeout handling,
argument sanitization, bounded result summaries, operational trace capture, and one bounded retry
for all eight tools. Every attempt remains visible in the trace. The orchestrator must not bypass
this package to access policy, employee data, or mock actions directly.
