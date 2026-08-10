# PeopleOps Assistant

PeopleOps Assistant is an agentic HR policy and operations application for the fictional Northstar Technologies Inc. It is being built as an AI engineering project that combines grounded policy retrieval, real Model Context Protocol (MCP) tool calls, synthetic employee data, safety controls, evaluation, and a deployable web interface.

> This repository contains synthetic educational data. It is not a production HR system and does not provide legal advice.

## Execution status

Phases 1 through 9 of the [authoritative execution plan](docs/execution-plan.md) are complete. Phase
10 implementation and automated evaluation are complete; the owner-controlled recorded demo and
final submission link checks remain. The repository currently provides:

- a FastAPI application with `/health`, `/chat`, bounded `/attachments/extract`, `/mcp`, and
  generated API documentation;
- an evidence-first React/Vite product workspace with employee navigation, five demo tasks, a
  use-case selector, bounded TXT/Markdown/PDF attachments, employee context, live health,
  citations, complete MCP trace, request/trace IDs, and explicit action confirmation;
- a validated 12-policy corpus in Markdown and PDF formats;
- typed configuration, policy-corpus validation, and MCP tool contracts;
- backend, frontend, corpus, and tool-contract tests;
- a multi-stage Docker build;
- SHA-pinned GitHub Actions checks for Python, web, container startup, and a real MCP workflow;
- an explicit pre-deployment release gate plus exact-commit hosted smoke verification;
- weekly grouped compatible-update maintenance for Actions, Python, npm, and Docker dependencies;
- architecture, developer, use-case, traceability, AI-tooling, and deployment documentation;
- ten GitHub phase milestones with acceptance-criteria issues;
- a strict runtime request, citation, tool-trace, response, and pending-action contract;
- a fixed synthetic as-of date of 2026-09-01, aligned with the policy corpus;
- 25 schema-valid gold evaluation cases and committed JSON Schemas;
- deterministic employee, manager, location, PTO, benefits, and historical ticket fixtures;
- strict mock-data schemas, checksums, semantic validation, and a reproducible SQLite build;
- a bounded orchestrator that discovers the complete eight-tool suite and invokes tools only through
  the official MCP client;
- typed, bounded international remote-work, PTO, and expense state machines with a ten-call
  logical ceiling (normal primary flows use at most eight; the optional draft uses nine) and one
  retry per MCP operation;
- clarification, structured-data, evidence-sufficiency, policy-conflict, exact-citation,
  escalation, draft, and confirmation gates;
- exact policy-section, employee-profile, PTO, benefits, deterministic compliance, structured
  unsent email-draft, and confirmation-gated mock-ticket capabilities alongside hybrid policy
  search;
- one shared timeout-controlled MCP executor with sanitized result traces for every tool;
- signed and expiring explicit-confirmation proof, exact action binding, idempotency, and an
  in-memory-only synthetic ticket store;
- direct ingestion of the authoritative ten Markdown and two PDF runtime policies;
- 169 heading-aware, metadata-enriched chunks and a persisted deterministic local embedding index;
- BM25-style keyword retrieval, local embedding similarity, hybrid ranking, query decomposition,
  deduplication, evidence coverage/conflict checks, and exact citation allow-listing;
- a retrieval ablation over 24 policy-evidence cases and 48 expected sections, with hybrid `k=8`
  selected at 100% gold evidence recall in the recorded Phase 5 run;
- repeatable cited remote-work and PTO primary workflows, a cited expense backup, and a complete
  preview/confirm/idempotent mock-ticket API sequence;
- a live Render deployment whose Blueprint waits for passing GitHub checks and exposes its exact
  release commit through `/health`;
- a replaceable OpenAI-compatible LLM adapter with OpenRouter configuration, authenticated model
  health, grounded-summary validation, deterministic fallback, and visible generation metadata;
- a network-free deterministic provider used by CI plus a bounded production-provider smoke gate
  that preserves sanitized evidence for every accepted or safely-fallbacked attempt;
- an executable 25-case gold evaluator with groundedness, citation, retrieval, tool-selection,
  workflow, clarification/escalation, action-safety, reliability, and latency evidence;
- executable assertions for every expected fact and answer constraint, including policy-snippet
  lexical/numeric support and structured-tool provenance, with all current gold gates at 100%;
- a 15-case intent-robustness gate covering paraphrases, common typos, aliases, mixed requests,
  confirmation-bypass attempts, and unsupported scope at 100%;
- a reproducible direct-dense feature-hash versus Sentence Transformers comparison that retains
  hybrid `k=8` on measured 100% evidence recall and lower deployment cost;
- three generic, read-only hosted provider observations with 100% workflow integrity and explicit
  accepted-provider versus safe-fallback metrics;
- a general corpus-grounded policy workflow covering benefits, onboarding, security, holidays,
  leave, conduct, privacy refusal, and policy-only compliance without inventing employee facts;
- a complete Phase 10 report, error analysis, submission checklist, and timed demo rehearsal;
- a maintained risk register with explicit controls, residual risks, owners, and non-goals.

See the [LLM provider guide](docs/llm-provider-integration.md),
[Phase 8 product-interface guide](docs/phase8-product-interface.md),
[Phase 7 workflow guide](docs/phase7-workflows.md),
[Phase 6 MCP guide](docs/phase6-mcp-tools.md),
[Phase 5 RAG guide](docs/phase5-rag.md), and
[Phase 4 workflow guide](docs/phase4-thin-slice.md) for the exact boundary. Release operation and
rollback are documented in the [Phase 9 CI/CD guide](docs/phase9-cicd-deployment.md). Complete
metrics and submission boundaries are in the
[Phase 10 evaluation guide](docs/phase10-evaluation-submission.md).

## Live demonstration

- Application: <https://peopleops-assistant-demo.onrender.com>
- Health: <https://peopleops-assistant-demo.onrender.com/health>
- API documentation: <https://peopleops-assistant-demo.onrender.com/docs>

The free service can require a cold start after inactivity. Wait for it to wake, then use the
E-1007 Germany preset or submit the documented PTO and expense prompts.

## Architecture

```text
Browser (React/Vite demonstration)
        |
        v
FastAPI (/health, /chat, /mcp)
        |
        +--> Bounded typed workflow state machines
        |          |
        |          v
        |     Official MCP client discovery
        |          |
        |          v
        |     PeopleOps MCP server (8 tools)
        |          |-- policy search + exact section
        |          |-- employee + PTO + benefits
        |          |-- deterministic compliance
        |          |-- structured draft-only HR email
        |          `-- confirmed in-memory mock ticket
        |
        +--> Hybrid RAG index (ready)
                   |
                   v
              169 validated sections

        +--> Mock-data validator / SQLite builder (ready)
                   |
                   v
              30 synthetic employees

        +--> LLM provider adapter (optional locally; OpenRouter-ready)
                   |
                   +-- grounded summary after verified workflow
                   `-- deterministic fallback on any provider/gating failure
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

Open `http://127.0.0.1:5173`. Vite proxies `/health`, `/chat`, and `/actions` to the backend during
development.

The workspace includes remote-work, PTO, expense, mock-ticket, and employee-neutral policy/benefits
guidance tasks. Select an employee, then select **Run task** to use that employee across every
employee-bound demo without a preset silently replacing the selection. The result shows exact policy
citations, request and trace IDs, employee context where required, and the complete MCP
discovery/call trace. The policy task omits the employee ID and proves that general guidance does not
access employee or benefits records.
The ticket task exposes an exact action preview and remains blocked until the user selects **Confirm
mock ticket**. See the Phase 8 guide for the complete grader walkthrough.

When an external provider is configured, the response header identifies the provider and resolved
model. The generated summary is shown above the unchanged verified workflow result. Disabled,
unavailable, or rejected provider output is labelled as deterministic or verified fallback.

## Automated validation

```powershell
.\scripts\check.ps1
```

The script runs schema drift and Phase 3 asset validation, Python linting and tests, web tests and
production build, and, when Docker is available, a production-image build plus startup/workflow
smoke. CI applies the same container contract before the release gate can pass.

Individual commands are documented in [docs/developer-guide.md](docs/developer-guide.md).

Run the complete committed evaluation evidence with:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_gold.py --write
.\.venv\Scripts\python.exe scripts\evaluate_intents.py --write
.\.venv\Scripts\python.exe scripts\evaluate_embeddings.py --check
.\.venv\Scripts\python.exe scripts\evaluate_hosted_provider.py --check
```

The current run executes all 25 cases and records 100% answer-fact accuracy, answer-constraint
adherence, claim support, groundedness, citation accuracy and coverage, tool selection, workflow
completion, clarification/escalation accuracy, action safety, and primary-demo completion. The
separate 15-case intent-robustness suite also passes in full. See the Phase 10 guide for definitions,
latency, reliability, embedding comparison, hosted-provider observations, and error analysis.

## Docker

```powershell
docker build -t peopleops-assistant:local .
docker run --rm -p 8000:8000 --env-file .env peopleops-assistant:local
```

The production image builds the React application and serves it from FastAPI.

## Project documentation

- [Use cases](docs/use-cases.md)
- [Phase 4 thin vertical slice](docs/phase4-thin-slice.md)
- [Phase 5 hybrid RAG](docs/phase5-rag.md)
- [Phase 6 MCP tool suite](docs/phase6-mcp-tools.md)
- [Phase 7 bounded workflows](docs/phase7-workflows.md)
- [Phase 8 product interface](docs/phase8-product-interface.md)
- [Phase 9 CI/CD and deployment](docs/phase9-cicd-deployment.md)
- [Phase 10 evaluation and submission](docs/phase10-evaluation-submission.md)
- [Risk register and known limitations](docs/risk-register.md)
- [Demo rehearsal](docs/demo-rehearsal.md)
- [Submission checklist](docs/submission-checklist.md)
- [LLM provider integration](docs/llm-provider-integration.md)
- [Score-5 UI design decision](docs/ui-design-decision.md)
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
