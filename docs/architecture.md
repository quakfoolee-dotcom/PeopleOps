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
    |-- /actions/mock-tickets/confirm
    `-- /mcp (Streamable HTTP)
    |
    v
Bounded typed workflow orchestrator
    |-- remote-work, PTO, expense, and mock-ticket state machines
    |-- classification, evidence, conflict, and confirmation gates
    |-- ten logical calls maximum; one bounded retry
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
- `app/agent`: typed workflow classification, state transitions, tool selection, and safety gates. It
  does not access data stores, RAG, tool implementations, or the action store directly.
- `app/services`: confirmation coordinator outside the agent data-access boundary; creation still
  occurs only through the MCP tool.
- `app/mcp_client`: official MCP client session plus shared timeout, sanitization, summary, and
  operational-trace boundary.
- `peopleops_mcp`: all eight implemented schemas, tools, Streamable HTTP server, and the isolated
  confirmation/action store.
- `policy_corpus`: authoritative runtime sources and human-review artifacts.
- `mock_data`: deterministic synthetic structured records and validation fixtures.
- `app/evaluation`: gold-suite schemas, loading, and semantic validation.
- `evaluation`: 25 gold cases, generated JSON Schemas, retrieval/tool artifacts, and the Phase 7
  workflow/safety evaluation; full gold-suite metrics remain Phase 10.
- `ui`: evidence-first React application built into static production assets; consumes only the
  public health, chat, and action-confirmation contracts.

## Phase 8 presentation boundary

The browser selects a synthetic employee, loads or runs a versioned task, and renders the typed
response. Citation and tool-trace inspectors are projections of API objects; the browser never reads
policy or data stores directly. A pending mock action is rendered from its sanitized preview. Only
the explicit confirm control calls the confirmation endpoint, after which the unchanged request ID,
employee, and message are resubmitted with proof that is neither displayed nor traced.

## Phase 7 bounded request sequence

1. `/chat` validates the strict request contract and fixed synthetic date.
2. Typed classification rejects unsupported or incomplete prompts before accessing tools.
3. The official MCP client discovers the server's current tool list.
4. The orchestrator verifies the selected workflow's required tools and applies the call budget.
5. `lookup_employee_profile` reads the validated synthetic snapshot.
6. Workflow-specific structured tools read PTO data or deterministic compliance calculations.
7. Hybrid search must report sufficient, conflict-free evidence, then each required section is
   fetched exactly and converted to an allow-listed citation.
8. The state machine returns conditional guidance, a non-persistent draft, a clarification, an
   escalation, or a confirmation preview. A confirmed mock create is idempotent.

## Phase 6 tool and action boundary

All policy and structured-data access occurs inside `peopleops_mcp`. The agent imports only MCP
schemas, the server's required tool-name set, and the client executor. An architectural test scans
the agent imports and rejects direct store, RAG, tool-implementation, or action-store access.

The ticket action uses two non-data state transitions before MCP invocation: prepare a preview, then
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
7. Relative dates, conflicting IDs, unknown destinations, and incomplete amounts are never silently
   resolved.
