# Requirements traceability

Status values: **Ready** means implemented and tested; **Foundation** means its boundary or contract exists; **Planned** means deliberately deferred to a named phase.

| Project requirement | Implementation or evidence | Status |
|---|---|---|
| Reproducible environment | `pyproject.toml`, `ui/package-lock.json`, `.env.example`, Dockerfile | Ready |
| Authoritative implementation sequence | `docs/execution-plan.md`, ten GitHub milestones, ten acceptance issues | Ready |
| Fixed synthetic as-of date | `app/core/constants.py`, `.env.example`, gold-suite validation | Ready |
| Strict API request/response contracts | `app/api/contracts.py`, generated JSON Schemas, contract tests | Ready |
| Stable citation contract | `Citation`, exact chunk/source metadata, corpus policy/section validation, generated schema | Ready |
| Sanitized operational trace contract | `ToolTraceEntry`, sensitive-key and error-state tests | Ready |
| Local web application | FastAPI and React/Vite setup instructions | Ready |
| `/health` endpoint | `app/api/health.py`, API tests, exact deployed release SHA | Ready |
| Policy corpus: 5-20 documents, 30-120 pages | 12-policy Northstar corpus, manifest and validation report | Ready |
| At least two source formats | 10 Markdown and 2 PDF runtime sources | Ready |
| Stable citation metadata | Policy manifest, section identifiers, `Citation` schema | Ready |
| RAG ingestion, chunking, index, retrieval | `app/rag`, persisted index, Markdown/PDF ingestion, hybrid retrieval, index drift check | Ready |
| Grounded answers and citation validation | Evidence coverage/conflict checks, exact retrieved-chunk allow-list, executable expected-fact/constraint assertions, and claim-to-citation/tool support | Ready: 100% gold gate |
| At least five MCP tools | Eight implemented typed MCP tools with input/output schemas | Ready |
| Actual MCP discovery and invocation | Official `mcp` client, Streamable HTTP server, eight-tool integration test | Ready |
| Two multi-step workflows | Repeatable remote-work and PTO state machines plus expense backup; Phase 7 evaluation | Ready |
| Operational tool trace | Shared executor records all eight tools with sanitized arguments, status, duration, and bounded summaries | Ready |
| Confirmation before write-like actions | Signed expiring confirmation, exact preview binding, idempotency, redaction, and safety tests | Ready |
| Synthetic structured data | 30 employees, 6 locations, manager, PTO, benefits, and ticket seeds; strict schemas, checksums, semantic validation, SQLite build | Ready |
| `/chat` endpoint and UI workflow | Five bounded API workflows plus typed decision summary, evidence-first workspace, real next actions, presets, employee context, citations, trace, identifiers, health, and confirmation dialog | Ready |
| Replaceable LLM provider | `app/providers`, environment factory, OpenRouter/OpenAI-compatible adapter, deterministic CI adapter, contract and orchestration tests | Ready |
| Grounded provider generation | Post-workflow-only summary, protected facts, exact citation allow-list, unknown identifier/number rejection, unchanged verified result, safe fallback | Ready |
| LLM provider health | Cached authenticated model probe, sanitized `/health` state, UI component status, bounded provider-aware hosted smoke with per-attempt evidence | Ready; production OpenRouter active |
| Automated startup test | FastAPI tests plus production-container startup and MCP workflow smoke | Ready |
| MCP discovery/call test | `tests/test_phase4_mcp.py`, `tests/test_phase4_chat.py`, `tests/test_phase6_mcp.py` | Ready |
| CI on push and pull request | SHA-pinned, timeout-bounded `.github/workflows/ci.yml` with retained test/smoke evidence | Ready |
| Deployment gated on passing tests | Explicit `release-gate`; Render `autoDeployTrigger: checksPass`; exact-commit post-deploy hosted smoke | Ready |
| Dependency-action maintenance | Weekly grouped compatible updates for Actions, pip, npm, and Docker; major/runtime-line migrations remain explicit | Ready |
| Release and rollback controls | Release identity in `/health`, runbook, immutable commit rollback, cold-start-aware smoke | Ready |
| Evaluation set of 20-30 cases | 25 machine-readable cases with exact 7/5/6/4/3 distribution | Ready |
| Evaluation expectations defined before implementation | Facts, policy sections, tools, outcomes, constraints, and safety per case | Ready |
| Evaluation and API JSON Schemas | `evaluation/schemas`, drift-export script, CI check | Ready |
| Required metrics and ablation | Phase 10 gold JSON/CSV: facts, constraints, claim support, groundedness, citations, tools, workflow, and safety 100%; hash/neural comparison plus Phase 5 retrieval ablation | Ready |
| Intent robustness | 15 versioned paraphrase, typo, country/date alias, mixed-intent, adversarial confirmation-bypass, and unsupported-scope cases | Ready: 100% |
| Production-provider evaluation | Three generic read-only hosted workflows; provider acceptance/fallback, latency, exact workflow/citation/tool integrity, and no-write checks | Ready: 100% integrity |
| README and design documentation | Root `README.md` and `design-and-evaluation.md` plus Phase 7–10 workflow, interface, release, evaluation, and submission guides | Ready |
| AI tooling disclosure | `ai-tooling.md` | Ready and maintained continuously |
| Deployment URL and cold-start notes | `render.yaml`, `deployed.md`, verified public root and `/health` | Ready |
| Recorded demo | Timed 8:30 script, two workflow diagrams, preflight, and rehearsal acceptance record | Ready to record; owner URL pending |
| Risk register and known limitations | `docs/risk-register.md`, mitigations, residual risk, owners, and verification evidence | Ready |
