# Agent package

Phase 7 implements typed remote-work, PTO, expense, and mock-ticket state machines over the official
MCP client. Classification and clarification occur before tool access; each selected workflow has a
fixed transition allow-list, an eight-call logical budget, and one retry per discovery or invocation.
Agent code must not import data stores, RAG, tool implementations, or the action store; the
architecture test enforces that boundary. Workflows expose sanitized operational traces, not hidden
chain-of-thought.
