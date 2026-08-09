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
| `/health` endpoint | `app/api/health.py`, API tests | Ready |
| Policy corpus: 5-20 documents, 30-120 pages | 12-policy Northstar corpus, manifest and validation report | Ready |
| At least two source formats | 10 Markdown and 2 PDF runtime sources | Ready |
| Stable citation metadata | Policy manifest, section identifiers, `Citation` schema | Ready |
| RAG ingestion, chunking, index, retrieval | `app/rag`, persisted index, Markdown/PDF ingestion, hybrid retrieval, index drift check | Ready |
| Grounded answers and citation validation | Evidence coverage/conflict checks, exact retrieved-chunk allow-list, citation tests | Ready: bounded workflow |
| At least five MCP tools | Eight implemented typed MCP tools with input/output schemas | Ready |
| Actual MCP discovery and invocation | Official `mcp` client, Streamable HTTP server, eight-tool integration test | Ready |
| Two multi-step workflows | Repeatable remote-work and PTO state machines plus expense backup; Phase 7 evaluation | Ready |
| Operational tool trace | Shared executor records all eight tools with sanitized arguments, status, duration, and bounded summaries | Ready |
| Confirmation before write-like actions | Signed expiring confirmation, exact preview binding, idempotency, redaction, and safety tests | Ready |
| Synthetic structured data | 30 employees, 6 locations, manager, PTO, benefits, and ticket seeds; strict schemas, checksums, semantic validation, SQLite build | Ready |
| `/chat` endpoint and UI workflow | Four bounded API workflows; evidence-first product workspace remains Phase 8 | Ready: workflow API |
| Automated startup test | FastAPI TestClient health and root tests | Ready |
| MCP discovery/call test | `tests/test_phase4_mcp.py`, `tests/test_phase4_chat.py`, `tests/test_phase6_mcp.py` | Ready |
| CI on push and pull request | `.github/workflows/ci.yml` | Ready |
| Deployment gated on passing tests | CI container depends on backend/frontend jobs; Render uses `autoDeployTrigger: checksPass` | Ready: initial service |
| Evaluation set of 20-30 cases | 25 machine-readable cases with exact 7/5/6/4/3 distribution | Ready |
| Evaluation expectations defined before implementation | Facts, policy sections, tools, outcomes, constraints, and safety per case | Ready |
| Evaluation and API JSON Schemas | `evaluation/schemas`, drift-export script, CI check | Ready |
| Required metrics and ablation | Phase 5 retrieval ablation and raw results; full workflow metrics remain Phase 10 | Foundation: retrieval ready |
| README and design documentation | Repository documentation and Phase 7 workflow/operator guide | Ready through Phase 7 |
| AI tooling disclosure | `ai-tooling.md` | Ready and maintained continuously |
| Deployment URL and cold-start notes | `render.yaml`, `deployed.md`, verified public root and `/health` | Ready |
| Recorded demo | Demo acceptance criteria in use cases | Planned: Phase 10 |
