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
| Actual MCP discovery and invocation | MCP client/server boundaries | Planned: Phase 4 |
| Two multi-step workflows | Remote-work and PTO use cases; expense backup | Planned: Phase 7 |
| Operational tool trace | Strict sanitized trace schema ready; runtime population planned | Foundation: Phase 4 |
| Confirmation before write-like actions | `create_mock_hr_ticket` contract and test | Foundation |
| Synthetic structured data | `mock_data` boundary and rules | Planned: Phase 3 |
| `/chat` endpoint and UI workflow | UI shell and architecture | Planned: Phases 4 and 8 |
| Automated startup test | FastAPI TestClient health and root tests | Ready |
| MCP discovery/call test | Contract test now | Planned: Phase 4 transport test |
| CI on push and pull request | `.github/workflows/ci.yml` | Ready |
| Deployment gated on passing tests | Container depends on backend/frontend jobs; deployment job deferred | Foundation |
| Evaluation set of 20-30 cases | 25 machine-readable cases with exact 7/5/6/4/3 distribution | Ready |
| Evaluation expectations defined before implementation | Facts, policy sections, tools, outcomes, constraints, and safety per case | Ready |
| Evaluation and API JSON Schemas | `evaluation/schemas`, drift-export script, CI check | Ready |
| Required metrics and ablation | `design-and-evaluation.md` | Planned: Phase 10 |
| README and design documentation | Repository documentation | Ready through Phase 2 |
| AI tooling disclosure | `ai-tooling.md` | Ready and maintained continuously |
| Deployment URL and cold-start notes | `deployed.md` | Planned: Phase 4 onward |
| Recorded demo | Demo acceptance criteria in use cases | Planned: Phase 10 |
