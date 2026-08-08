# Design and evaluation

## Design decisions

- **Deployment:** one container with logically separated modules to reduce free-tier operational risk.
- **API:** FastAPI for typed schemas, health checks, and asynchronous integration points.
- **Web:** React and Vite compiled to static assets served by FastAPI in production.
- **MCP:** eight tool contracts with future discovery and invocation through a dedicated client/server boundary.
- **Corpus:** 12 coherent synthetic policies with 10 Markdown and 2 PDF authoritative runtime sources.
- **Structured data:** deterministic synthetic records; no real personal information.
- **Safety:** bounded tool calls, evidence sufficiency, citation allow-listing, explicit confirmation for persistent mock actions, and controlled degraded-mode responses.
- **Testing:** deterministic substitutes in CI; live providers are not required for ordinary pull requests.

## Evaluation design

The project uses 25 pre-implementation gold cases:

| Category | Cases |
|---|---:|
| Straightforward policy questions | 7 |
| Multi-document policy questions | 5 |
| Employee-specific and tool workflows | 6 |
| Ambiguous requests requiring clarification | 4 |
| Out-of-scope, escalation, and safety | 3 |

Each case identifies expected facts, policy sections, required, forbidden, and post-confirmation tools, expected workflow outcome, answer constraints, and action-safety behavior. The fixed synthetic as-of date is **2026-09-01**, matching the policy corpus effective date. `evaluation/gold_cases.json` is validated against Pydantic contracts, corpus section headings, MCP tool names, and the required category distribution.

## Metrics

- groundedness of material claims;
- citation accuracy and retrieval evidence recall;
- tool-selection accuracy;
- workflow completion;
- clarification and escalation accuracy;
- action-safety pass rate;
- warm latency p50 and p95;
- cold-start latency reported separately.

The retrieval ablation will compare dense-only retrieval at `k=5`, hybrid retrieval at `k=5`, and hybrid retrieval at `k=8`. Production settings will be selected from evidence quality and latency results.

## Current evidence

Phases 1 through 3 validate startup, health reporting, the 12-policy/45-page corpus, product naming, MCP tool contracts, the web shell, container construction, runtime data contracts, schema drift checks, the 25-case gold suite, and the deterministic 30-employee operational snapshot. Phase 3 additionally proves checksum integrity, cross-record consistency, an acyclic manager hierarchy, date alignment, synthetic-only enforcement, and a foreign-key-clean SQLite build. These phases do not claim RAG, MCP transport, agent workflow, or answer-quality results before those components exist.
