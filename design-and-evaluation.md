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
- **LLM provider:** replaceable OpenAI-compatible post-workflow synthesis; the model cannot select
  tools, change decisions, create citations, or authorize actions.

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

The Phase 5/10 retrieval ablation compares dense-only retrieval at `k=5`, hybrid retrieval at `k=5`,
and hybrid retrieval at `k=8`. Across the 24 cases with policy evidence and 48 exact expected
sections, the measured recalls were 83.33%, 95.83%, and 100.00%, respectively. Hybrid `k=8` is the
selected configuration.

The complete Phase 10 run executes all 25 cases through the real orchestrator and MCP boundary. It
records 96% groundedness, 100% citation accuracy and coverage, 100% retrieval evidence recall,
100% tool-selection accuracy, 96% workflow completion, 100% clarification/escalation accuracy,
100% action safety, and 100% primary-demo completion. Both primary workflows completed ten
consecutive warm runs with repeatable verified results. Local deterministic-provider latency was
1,045 ms for the first-process primary request and 226 ms p50 / 363 ms p95 across 20 warm cases.
See `docs/phase10-evaluation-submission.md` for definitions and error analysis.

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

The Phase 8 interface suite verifies the grader-visible evidence path: live health, preset loading,
employee selection and context, cited results, complete operational trace, request and trace IDs,
explicit confirmation, request-bound creation, token non-rendering, and cancel-without-create.

The provider suite verifies OpenRouter request/authentication shape, one bounded transient retry,
authenticated cached model health, credential redaction, structured JSON parsing, exact citation
coverage, protected facts, unknown fact rejection, provider-mode orchestration, and deterministic
fallback. CI exercises this boundary without network access; production evidence requires the
owner-configured secret and provider-aware hosted smoke.

## Current evidence

Phases 1 through 8 validate startup and health reporting; the 12-policy/45-page corpus; deterministic
structured data; API and evaluation contracts; live MCP discovery and calls; the bounded deployed
workflow; direct Markdown and PDF ingestion; a persisted 169-section hybrid index; evidence
sufficiency and conflict behavior; citation allow-listing; and 100% retrieval evidence recall for
the selected Phase 5 configuration. Phase 6 additionally proves eight schema-valid tools, shared
timeouts and sanitized traces, read-only structured-data operations, deterministic compliance,
draft-only email behavior, confirmation-gated idempotent mock actions, and typed remote-work, PTO,
expense, and ticket workflows with clarification, retry, evidence, conflict, citation, escalation,
and confirmation gates. Phase 8 adds the responsive evidence-first product workspace and interactive
confirmation experience. The provider integration adds bounded grounded synthesis and safe fallback.
Phase 10 completes the automated gold-suite evaluation and submission evidence. One deliberately
reported case misses its expected confirmation outcome because its prompt omits the affected
employee ID; the assistant cites the confirmation rule and requests the missing identifier rather
than inventing a person. This keeps action safety at 100% and workflow completion at 96%, above the
predeclared internal target. The human-recorded presentation and final link/access checks remain
owner-controlled submission steps.
