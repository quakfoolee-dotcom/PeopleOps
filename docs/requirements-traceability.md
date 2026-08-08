# Requirements traceability

Status values: **Ready** means implemented and tested; **Foundation** means its boundary or contract exists; **Planned** means deliberately deferred to a named milestone.

| Project requirement | Implementation or evidence | Status |
|---|---|---|
| Reproducible environment | `pyproject.toml`, `ui/package-lock.json`, `.env.example`, Dockerfile | Ready |
| Local web application | FastAPI and React/Vite setup instructions | Ready |
| `/health` endpoint | `app/api/health.py`, API tests | Ready |
| Policy corpus: 5-20 documents, 30-120 pages | 12-policy Northstar corpus, manifest and validation report | Ready |
| At least two source formats | 10 Markdown and 2 PDF runtime sources | Ready |
| Stable citation metadata | Policy manifest and section identifiers | Ready |
| RAG ingestion, chunking, index, retrieval | `app/rag` boundary and canonical corpus | Planned: retrieval milestone |
| Grounded answers and citation validation | Architecture and use-case acceptance criteria | Planned: retrieval milestone |
| At least five MCP tools | Eight typed tool contracts | Foundation |
| Actual MCP discovery and invocation | MCP client/server boundaries | Planned: MCP vertical slice |
| Two multi-step workflows | Remote-work and PTO use cases; expense backup | Planned: workflow milestone |
| Operational tool trace | Trace fields specified in use cases and architecture | Planned: MCP vertical slice |
| Confirmation before write-like actions | `create_mock_hr_ticket` contract and test | Foundation |
| Synthetic structured data | `mock_data` boundary and rules | Planned: data milestone |
| `/chat` endpoint and UI workflow | UI shell and architecture | Planned: workflow milestone |
| Automated startup test | FastAPI TestClient health and root tests | Ready |
| MCP discovery/call test | Contract test now | Planned: transport test in MCP milestone |
| CI on push and pull request | `.github/workflows/ci.yml` | Ready |
| Deployment gated on passing tests | Container depends on backend/frontend jobs; deployment job deferred | Foundation |
| Evaluation set of 20-30 cases | Evaluation design and directory | Planned: evaluation-first data milestone |
| Required metrics and ablation | `design-and-evaluation.md` | Planned: evaluation milestone |
| README and design documentation | Repository documentation | Ready for foundation |
| AI tooling disclosure | `ai-tooling.md` | Ready and maintained continuously |
| Deployment URL and cold-start notes | `deployed.md` | Planned: deployment milestone |
| Recorded demo | Demo acceptance criteria in use cases | Planned: final milestone |
