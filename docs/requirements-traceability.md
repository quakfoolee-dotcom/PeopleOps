# Requirements traceability

Status values: **Ready** means implemented and tested; **Foundation** means its boundary or contract exists; **Planned** means deliberately deferred to a named phase.

| Project requirement | Implementation or evidence | Status |
|---|---|---|
| Reproducible environment | `pyproject.toml`, `ui/package-lock.json`, `.env.example`, Dockerfile | Ready |
| Authoritative implementation sequence | `docs/execution-plan.md`, ten GitHub milestones, ten acceptance issues | Ready |
| Fixed synthetic as-of date | `app/core/constants.py`, `.env.example`, gold-suite validation | Ready |
| Strict API request/response contracts | `app/api/contracts.py`, generated JSON Schemas, contract tests | Ready |
| Stable citation contract | `Citation`, corpus policy/section validation, generated schema | Ready |
| Sanitized operational trace contract | `ToolTraceEntry`, sensitive-key and error-state tests | Ready |
| Local web application | FastAPI and React/Vite setup instructions | Ready |
| `/health` endpoint | `app/api/health.py`, API tests | Ready |
| Policy corpus: 5-20 documents, 30-120 pages | 12-policy Northstar corpus, manifest and validation report | Ready |
| At least two source formats | 10 Markdown and 2 PDF runtime sources | Ready |
| Stable citation metadata | Policy manifest, section identifiers, `Citation` schema | Ready |
| RAG ingestion, chunking, index, retrieval | `app/rag` boundary and canonical corpus | Planned: Phase 5 |
| Grounded answers and citation validation | Architecture and use-case acceptance criteria | Planned: Phase 5 |
| At least five MCP tools | Eight typed tool contracts | Foundation |
| Actual MCP discovery and invocation | Official `mcp` client, Streamable HTTP server, Phase 4 integration test | Ready: 2-tool slice |
| Two multi-step workflows | Remote-work and PTO use cases; expense backup | Planned: Phase 7 |
| Operational tool trace | `/chat` response and UI show discovery/call summaries, sanitized arguments, status, and duration | Ready: Phase 4 slice |
| Confirmation before write-like actions | `create_mock_hr_ticket` contract and test | Foundation |
| Synthetic structured data | 30 employees, 6 locations, manager, PTO, benefits, and ticket seeds; strict schemas, checksums, semantic validation, SQLite build | Ready |
| `/chat` endpoint and UI workflow | Bounded API path and E-1007 live demonstration; broader product work remains | Ready: Phase 4 slice |
| Automated startup test | FastAPI TestClient health and root tests | Ready |
| MCP discovery/call test | `tests/test_phase4_mcp.py`, `tests/test_phase4_chat.py` | Ready |
| CI on push and pull request | `.github/workflows/ci.yml` | Ready |
| Deployment gated on passing tests | CI container depends on backend/frontend jobs; Render uses `autoDeployTrigger: checksPass` | Ready: initial service |
| Evaluation set of 20-30 cases | 25 machine-readable cases with exact 7/5/6/4/3 distribution | Ready |
| Evaluation expectations defined before implementation | Facts, policy sections, tools, outcomes, constraints, and safety per case | Ready |
| Evaluation and API JSON Schemas | `evaluation/schemas`, drift-export script, CI check | Ready |
| Required metrics and ablation | `design-and-evaluation.md` | Planned: Phase 10 |
| README and design documentation | Repository documentation | Ready through Phase 4 |
| AI tooling disclosure | `ai-tooling.md` | Ready and maintained continuously |
| Deployment URL and cold-start notes | `render.yaml`, `deployed.md`, verified public root and `/health` | Ready |
| Recorded demo | Demo acceptance criteria in use cases | Planned: Phase 10 |
