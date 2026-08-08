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

The project will use 25 gold cases:

| Category | Cases |
|---|---:|
| Straightforward policy questions | 7 |
| Multi-document policy questions | 5 |
| Employee-specific and tool workflows | 6 |
| Ambiguous requests requiring clarification | 4 |
| Out-of-scope, escalation, and safety | 3 |

Each case will identify expected facts, policy sections, required and forbidden tools, expected workflow outcome, clarification or escalation behavior, and action-safety behavior.

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

Milestone 1 validates startup, health reporting, the policy corpus, product naming, MCP tool contracts, the web shell, and container construction. It does not claim RAG, MCP transport, agent workflow, or answer-quality results before those components exist.
