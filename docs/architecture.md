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
Bounded Phase 4 orchestrator
    |-- fixed workflow and evidence gate
    |-- typed response and citations
    `-- sanitized operational trace
    |
    v
Official MCP client -> MCP server
               |-- lookup_employee_profile (live)
               |-- search_policy_documents (live)
               `-- six additional contracts (Phase 6)
                    |                 |
                    v                 v
             Policy RAG index   Synthetic data store
                    |
                    v
              LLM provider adapter
```

## Foundation boundaries

- `app/api`: HTTP endpoints plus strict request, citation, trace, action-preview, and response contracts.
- `app/core`: environment-driven configuration.
- `app/rag`: corpus validation now; Phase 5 ingestion and hybrid retrieval next.
- `app/agent`: bounded Phase 4 orchestration. It does not access data stores directly.
- `app/mcp_client`: official MCP client session boundary.
- `peopleops_mcp`: all eight contracts plus the Streamable HTTP server and two live Phase 4 tools.
- `policy_corpus`: authoritative runtime sources and human-review artifacts.
- `mock_data`: future deterministic synthetic structured records.
- `app/evaluation`: gold-suite schemas, loading, and semantic validation.
- `evaluation`: 25 gold cases and generated JSON Schemas now; metrics, latency, and ablation results in Phase 10.
- `ui`: React application built into static production assets.

## Phase 4 request sequence

1. `/chat` validates the strict request contract and fixed synthetic date.
2. The orchestrator rejects unsupported prompts before accessing tools.
3. The official MCP client discovers the server's current tool list.
4. The orchestrator requires both Phase 4 tools before continuing.
5. `lookup_employee_profile` reads the validated synthetic snapshot.
6. `search_policy_documents` extracts stable sections from authoritative policy sources.
7. The orchestrator produces a typed conditional answer, citations, and sanitized timing trace.

This deterministic slice validates the protocol and security boundary. It is not a replacement for
the hybrid RAG and wider state machine planned in Phases 5 and 7.

## Safety principles

1. Retrieved documents are untrusted source content, never executable instructions.
2. Final policy claims must cite identifiers returned by retrieval.
3. Missing evidence or structured data produces clarification or escalation, not fabrication.
4. Persistent mock actions require explicit user confirmation.
5. Operational traces show tool names, arguments, outcomes, and evidence without hidden chain-of-thought.
6. All people and records remain synthetic.
