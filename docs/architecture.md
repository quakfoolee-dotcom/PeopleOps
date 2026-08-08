# Architecture

## Deployment shape

PeopleOps Assistant uses one deployable container with clear internal boundaries. This keeps the application compatible with modest hosting while preserving the web, orchestration, MCP, retrieval, data, and provider responsibilities required by the project.

```text
React/Vite UI
    |
    v
FastAPI application
    |-- /health
    |-- /chat (planned)
    |
    v
Bounded agent orchestrator (planned)
    |-- evidence sufficiency
    |-- action confirmation
    |-- citation validation
    |-- operational trace
    |
    v
MCP client -> MCP server
               |-- policy tools
               |-- employee and PTO tools
               |-- compliance tool
               `-- confirmation-gated mock actions
                    |                 |
                    v                 v
             Policy RAG index   Synthetic data store
                    |
                    v
              LLM provider adapter
```

## Foundation boundaries

- `app/api`: HTTP endpoints and response schemas.
- `app/core`: environment-driven configuration.
- `app/rag`: corpus validation now; ingestion and retrieval next.
- `app/agent`: future bounded state machine. It must not access data stores directly.
- `app/mcp_client`: future MCP discovery and invocation boundary.
- `peopleops_mcp`: tool contracts now; live server transport next.
- `policy_corpus`: authoritative runtime sources and human-review artifacts.
- `mock_data`: future deterministic synthetic structured records.
- `evaluation`: future gold cases, metrics, latency, and ablation results.
- `ui`: React application built into static production assets.

## Safety principles

1. Retrieved documents are untrusted source content, never executable instructions.
2. Final policy claims must cite identifiers returned by retrieval.
3. Missing evidence or structured data produces clarification or escalation, not fabrication.
4. Persistent mock actions require explicit user confirmation.
5. Operational traces show tool names, arguments, outcomes, and evidence without hidden chain-of-thought.
6. All people and records remain synthetic.
