# PeopleOps Assistant

PeopleOps Assistant is an agentic HR policy and operations application for the fictional Northstar Technologies Inc. It is being built as an AI engineering project that combines grounded policy retrieval, real Model Context Protocol (MCP) tool calls, synthetic employee data, safety controls, evaluation, and a deployable web interface.

> This repository contains synthetic educational data. It is not a production HR system and does not provide legal advice.

## Execution status

Phases 1 through 3 and the implementation portion of Phase 4 of the [authoritative execution plan](docs/execution-plan.md) are complete. The repository currently provides:

- a FastAPI application with `/health`, `/chat`, `/mcp`, and generated API documentation;
- a React and Vite demonstration interface with citations and an MCP trace;
- a validated 12-policy corpus in Markdown and PDF formats;
- typed configuration, policy-corpus validation, and MCP tool contracts;
- backend, frontend, corpus, and tool-contract tests;
- a multi-stage Docker build;
- GitHub Actions checks for Python, web, and container builds;
- architecture, developer, use-case, traceability, AI-tooling, and deployment documentation;
- ten GitHub phase milestones with acceptance-criteria issues;
- a strict runtime request, citation, tool-trace, response, and pending-action contract;
- a fixed synthetic as-of date of 2026-09-01, aligned with the policy corpus;
- 25 schema-valid gold evaluation cases and committed JSON Schemas;
- deterministic employee, manager, location, PTO, benefits, and historical ticket fixtures;
- strict mock-data schemas, checksums, semantic validation, and a reproducible SQLite build.
- a bounded orchestrator that discovers and invokes two read-only tools through the official MCP client;
- a cited E-1007 international remote-work demonstration with fail-closed behavior;
- a Render Blueprint whose deploy trigger waits for passing GitHub checks.

Hybrid RAG, the other six MCP tools, broader workflows, confirmation-gated writes, and provider-backed generation remain deliberately deferred to later phases. See [the Phase 4 guide](docs/phase4-thin-slice.md) for the exact boundary.

## Architecture

```text
Browser (React/Vite demonstration)
        |
        v
FastAPI (/health, /chat, /mcp)
        |
        +--> Bounded orchestrator
        |          |
        |          v
        |     Official MCP client discovery
        |          |
        |          v
        |     PeopleOps MCP server
        |          |-- lookup_employee_profile
        |          `-- search_policy_documents
        |
        +--> Policy corpus validator (ready)
                   |
                   v
              12 synthetic policies

        +--> Mock-data validator / SQLite builder (ready)
                   |
                   v
              30 synthetic employees
```

See [docs/architecture.md](docs/architecture.md) for component boundaries and [docs/requirements-traceability.md](docs/requirements-traceability.md) for rubric coverage.

## Prerequisites

- Python 3.12 or newer
- Node.js 22 or newer
- Docker Desktop, optional but recommended

## Local setup

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Open:

- API root: `http://127.0.0.1:8000/`
- Health: `http://127.0.0.1:8000/health`
- API documentation: `http://127.0.0.1:8000/docs`
- MCP endpoint: `http://127.0.0.1:8000/mcp`

### Web interface

In a second terminal:

```powershell
Set-Location ui
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/health` and `/chat` to the backend during development.

The page includes a preset E-1007 Germany request. Select **Run cited workflow** to see the
conditional answer, four policy citations, request ID, and MCP discovery/call trace.

## Automated validation

```powershell
.\scripts\check.ps1
```

The script runs schema drift and Phase 3 asset validation, Python linting and tests, web tests and production build, and a Docker build when Docker is available.

Individual commands are documented in [docs/developer-guide.md](docs/developer-guide.md).

## Docker

```powershell
docker build -t peopleops-assistant:local .
docker run --rm -p 8000:8000 --env-file .env peopleops-assistant:local
```

The production image builds the React application and serves it from FastAPI.

## Project documentation

- [Use cases](docs/use-cases.md)
- [Phase 4 thin vertical slice](docs/phase4-thin-slice.md)
- [Developer guide](docs/developer-guide.md)
- [Architecture](docs/architecture.md)
- [Requirements traceability](docs/requirements-traceability.md)
- [Authoritative execution plan](docs/execution-plan.md)
- [Data contracts and evaluation guide](docs/data-contracts.md)
- [Design and evaluation](design-and-evaluation.md)
- [AI tooling disclosure](ai-tooling.md)
- [Deployment status](deployed.md)
- [Policy corpus guide](policy_corpus/README.md)
- [Synthetic data guide](mock_data/README.md)
