# Architecture

## Deployment shape

PeopleOps Assistant uses one deployable container with clear internal boundaries. This keeps the application compatible with modest hosting while preserving the web, orchestration, MCP, retrieval, data, and provider responsibilities required by the project.

```text
React/Vite UI
    |
    v
FastAPI application
    |-- /health
    |-- /chat
    `-- /mcp (Streamable HTTP)
    |
    v
Bounded international-work orchestrator
    |-- fixed workflow and evidence gate
    |-- typed response and citations
    `-- sanitized operational trace
    |
    v
Official MCP client -> MCP server
               |-- policy search + exact section
               |-- employee + PTO + benefits
               |-- deterministic compliance
               |-- draft-only email
               `-- confirmed in-memory mock ticket
                    |                 |
                    v                 v
             Hybrid RAG index   Synthetic data + action stores
                    |
                    v
              LLM provider adapter
```

## Foundation boundaries

- `app/api`: HTTP endpoints plus strict request, citation, trace, action-preview, and response contracts.
- `app/core`: environment-driven configuration.
- `app/rag`: authoritative Markdown/PDF ingestion, enriched chunks, local embeddings, BM25-style
  keyword scoring, hybrid ranking, query decomposition, evidence checks, and citation validation.
- `app/agent`: bounded international-work orchestration. It does not access data stores or RAG directly.
- `app/mcp_client`: official MCP client session plus shared timeout, sanitization, summary, and
  operational-trace boundary.
- `peopleops_mcp`: all eight implemented schemas, tools, Streamable HTTP server, and the isolated
  confirmation/action store.
- `policy_corpus`: authoritative runtime sources and human-review artifacts.
- `mock_data`: future deterministic synthetic structured records.
- `app/evaluation`: gold-suite schemas, loading, and semantic validation.
- `evaluation`: 25 gold cases, generated JSON Schemas, and Phase 5 retrieval ablation artifacts;
  full workflow metrics remain Phase 10.
- `ui`: React application built into static production assets.

## Current bounded request sequence

1. `/chat` validates the strict request contract and fixed synthetic date.
2. The orchestrator rejects unsupported prompts before accessing tools.
3. The official MCP client discovers the server's current tool list.
4. The orchestrator verifies that the complete eight-tool Phase 6 suite is available.
5. `lookup_employee_profile` reads the validated synthetic snapshot.
6. `search_policy_documents` loads the persisted hybrid index, decomposes the query, applies hybrid
   ranking and evidence coverage, validates citations, and returns enriched evidence.
7. The orchestrator produces a typed conditional answer, citations, and sanitized timing trace.

The workflow remains bounded while Phase 7 adds the wider state machine. The remaining tools are
already independently exercised through the same official client and traced executor.

## Phase 6 tool and action boundary

All policy and structured-data access occurs inside `peopleops_mcp`. The agent imports only MCP
schemas, the server's required tool-name set, and the client executor. An architectural test scans
the agent imports and rejects direct store, RAG, tool-implementation, or action-store access.

The ticket action uses two non-tool state transitions before MCP invocation: prepare a preview, then
record explicit user confirmation and mint signed proof. The MCP create tool validates the proof,
expiry, exact preview fingerprint, and idempotency key. Its only mutation is a process-local synthetic
record; source fixtures and external HR systems are never changed.

## Safety principles

1. Retrieved documents are untrusted source content, never executable instructions.
2. Final policy claims must cite identifiers returned by retrieval.
3. Missing evidence or structured data produces clarification or escalation, not fabrication.
4. Mock actions require signed, expiring, exact-preview user confirmation and idempotency.
5. Operational traces show tool names, arguments, outcomes, and evidence without hidden chain-of-thought.
6. All people and records remain synthetic.
