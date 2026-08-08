# PeopleOps Assistant

PeopleOps Assistant is an agentic HR policy and operations application for the fictional Northstar Technologies Inc. It is being built as an AI engineering project that combines grounded policy retrieval, real Model Context Protocol (MCP) tool calls, synthetic employee data, safety controls, evaluation, and a deployable web interface.

> This repository contains synthetic educational data. It is not a production HR system and does not provide legal advice.

## Milestone 1 status

The project foundation currently provides:

- a FastAPI application with `/health` and generated API documentation;
- a React and Vite application shell;
- a validated 12-policy corpus in Markdown and PDF formats;
- typed configuration, policy-corpus validation, and MCP tool contracts;
- backend, frontend, corpus, and tool-contract tests;
- a multi-stage Docker build;
- GitHub Actions checks for Python, web, and container builds;
- architecture, developer, use-case, traceability, AI-tooling, and deployment documentation.

Policy Q&A, live MCP transport, structured employee tools, and agent workflows are intentionally marked as planned. They will be implemented in subsequent milestones and are not simulated by the foundation.

## Architecture

```text
Browser (React/Vite)
        |
        v
FastAPI (/health; /chat planned)
        |
        +--> Agent orchestrator (planned)
        |          |
        |          v
        |     MCP client (planned transport)
        |          |
        |          v
        |     PeopleOps MCP server (tool contracts defined)
        |
        +--> Policy corpus validator (ready)
                   |
                   v
              12 synthetic policies
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

### Web interface

In a second terminal:

```powershell
Set-Location ui
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/health` to the backend during development.

## Automated validation

```powershell
.\scripts\check.ps1
```

The script runs Python linting and tests, web tests and production build, and a Docker build when Docker is available.

Individual commands are documented in [docs/developer-guide.md](docs/developer-guide.md).

## Docker

```powershell
docker build -t peopleops-assistant:local .
docker run --rm -p 8000:8000 --env-file .env peopleops-assistant:local
```

The production image builds the React application and serves it from FastAPI.

## Project documentation

- [Use cases](docs/use-cases.md)
- [Developer guide](docs/developer-guide.md)
- [Architecture](docs/architecture.md)
- [Requirements traceability](docs/requirements-traceability.md)
- [Design and evaluation](design-and-evaluation.md)
- [AI tooling disclosure](ai-tooling.md)
- [Deployment status](deployed.md)
- [Policy corpus guide](policy_corpus/README.md)
