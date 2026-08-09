# Agent package

The current bounded international-work workflow uses the official MCP client and requires discovery
of the complete eight-tool suite. Phase 7 expands it into typed remote-work, PTO, and expense state
machines. Agent code must not import data stores, RAG, tool implementations, or the action store;
the Phase 6 architecture test enforces that boundary. Workflows expose sanitized operational traces,
not hidden chain-of-thought.
