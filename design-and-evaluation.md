# Design and evaluation

## Design decisions

- **Deployment:** one container with logically separated modules to reduce free-tier operational risk.
- **API:** FastAPI for typed schemas, health checks, and asynchronous integration points.
- **Web:** React and Vite compiled to static assets served by FastAPI in production.
- **MCP:** eight implemented tools discovered and invoked through a dedicated client/server boundary.
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

The Phase 6 machine-readable tool validation discovered all eight tools, found input and output
schemas for all eight, completed one traced call per tool, rejected an unsigned ticket action,
returned the same mock ticket for an idempotent repeat, omitted the confirmation token from traces,
and verified the committed ticket seed was unchanged. These are tool-layer results, not full
workflow-selection metrics.

The Phase 7 focused workflow evaluation repeats the remote-work and PTO primary workflows three
times each, exercises the expense backup, and records exact citations and bounded tool paths. It
also proves no-tool clarification for missing identity and ambiguous dates, fail-closed unavailable
service behavior, policy-conflict escalation, preview-before-create confirmation, idempotency,
token redaction, and unchanged fixtures.

## Current evidence

Phases 1 through 7 validate startup and health reporting; the 12-policy/45-page corpus; deterministic
structured data; API and evaluation contracts; live MCP discovery and calls; the bounded deployed
workflow; direct Markdown and PDF ingestion; a persisted 169-section hybrid index; evidence
sufficiency and conflict behavior; citation allow-listing; and 100% retrieval evidence recall for
the selected Phase 5 configuration. Phase 6 additionally proves eight schema-valid tools, shared
timeouts and sanitized traces, read-only structured-data operations, deterministic compliance,
draft-only email behavior, confirmation-gated idempotent mock actions, and typed remote-work, PTO,
expense, and ticket workflows with clarification, retry, evidence, conflict, citation, escalation,
and confirmation gates. The final product workspace, provider generation, and complete gold-suite
evaluation are not yet complete.
