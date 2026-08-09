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

The Phase 5 retrieval ablation compares dense-only retrieval at `k=5`, hybrid retrieval at `k=5`,
and hybrid retrieval at `k=8`. Across the 24 cases with policy evidence and 48 exact expected
sections, the measured recalls were 83.33%, 95.83%, and 100.00%, respectively. Hybrid `k=8` is the
selected configuration. Full groundedness, tool, workflow, safety, and deployed latency metrics
remain Phase 10 work.

## Current evidence

Phases 1 through 5 validate startup and health reporting; the 12-policy/45-page corpus; deterministic
structured data; API and evaluation contracts; live MCP discovery and calls; the bounded deployed
workflow; direct Markdown and PDF ingestion; a persisted 169-section hybrid index; evidence
sufficiency and conflict behavior; citation allow-listing; and 100% retrieval evidence recall for
the selected Phase 5 configuration. This retrieval result does not claim that the still-planned
eight-tool suite, broader workflows, provider generation, or final product evaluation is complete.
