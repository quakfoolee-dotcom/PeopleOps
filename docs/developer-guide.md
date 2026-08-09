# Developer guide

## Repository workflow

1. Start from an up-to-date `main` branch.
2. Keep secrets in `.env`; never commit `.env` or credentials.
3. Add or update automated tests with each behavior change.
4. Run `scripts/check.ps1` before publishing.
5. Keep `ai-tooling.md` current whenever AI tools materially assist development.

## Backend commands

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m ruff check .
python scripts/export_contract_schemas.py --check
python scripts/validate_phase3_assets.py
python scripts/build_rag_index.py --check
python scripts/evaluate_mcp_tools.py
python scripts/evaluate_workflows.py
python -m pytest --cov=app --cov=peopleops_mcp --cov-report=term-missing
uvicorn app.main:app --reload
```

## Web commands

```powershell
Set-Location ui
npm install
npm run test
npm run build
npm run dev
```

If a managed Windows network inspects HTTPS traffic, set `NODE_USE_SYSTEM_CA=1` for local npm commands so Node uses the Windows trusted certificate store. Keep normal certificate verification enabled.

## Corpus handling

Only `policy_corpus/runtime_corpus` is authoritative for retrieval. Do not ingest it alongside `master_markdown`, `review_pdfs`, or the combined handbook, because those contain duplicate representations.

When changing a policy:

1. Update its master Markdown source.
2. Regenerate the corresponding runtime and review artifact.
3. Update the manifest and consistency matrix.
4. Re-run corpus validation and retrieval tests.
5. Preserve stable policy and section identifiers unless a documented migration is required.
6. Run `python scripts/build_rag_index.py`, commit the regenerated index, and run the retrieval
   evaluation.

## RAG development

Rebuild and verify the deterministic index:

```powershell
python scripts/build_rag_index.py
python scripts/build_rag_index.py --check
```

Run and optionally refresh the Phase 5 retrieval ablation:

```powershell
python scripts/evaluate_rag.py
python scripts/evaluate_rag.py --write
```

The authoritative settings are `RAG_INDEX_PATH`, `RAG_EMBEDDING_DIMENSIONS`,
`RAG_CHUNK_TARGET_WORDS`, `RAG_CHUNK_OVERLAP_WORDS`, and `RAG_TOP_K`. A change to embedding or
chunk behavior must bump its version, rebuild the persisted artifact, and preserve at least 95%
gold evidence recall for the selected configuration.

## Synthetic operational data

The committed source of truth is `mock_data/seed`; generated database files are disposable and ignored. Validate the full policy-and-data package with:

```powershell
python scripts/validate_phase3_assets.py
```

Build a local SQLite copy when needed for development:

```powershell
python scripts/validate_phase3_assets.py --database mock_data/generated/peopleops.db
```

The build is accepted only after strict schema, checksum, cross-record, date, manager-hierarchy, and SQLite foreign-key validation succeeds. See `mock_data/README.md` for the fixture contract and safe change procedure.

## Configuration

Copy `.env.example` to `.env`. Provider keys are intentionally absent from the example. Future provider-specific keys must be read from the environment and must never be returned by `/health`.

`SYNTHETIC_AS_OF_DATE` defaults to `2026-09-01`, matching the policy corpus effective date. Keep that value fixed for ordinary automated tests and gold-suite runs. A deliberate date change requires updating the gold suite, mock-data snapshot, generated schemas where applicable, tests, and evaluation documentation together.

`MCP_SERVER_URL` defaults to `http://127.0.0.1:8000/mcp`. The combined FastAPI process mounts the
MCP Streamable HTTP application at that path, so `/chat` exercises a real client/server boundary
without a second container. Do not point the orchestrator at a data store or corpus path.

`MCP_CONFIRMATION_SECRET` signs the Phase 6 mock-action confirmation proof and must be at least 32
characters. Render generates the production value. The `.env.example` value is local-demo-only.
`MCP_CONFIRMATION_TTL_SECONDS` defaults to 900 seconds. Never log or add the token to an operational
trace.

## Phase 6 MCP verification

Run the complete tool-layer tests:

```powershell
python -m pytest tests/test_phase6_tool_data.py `
  tests/test_phase6_action_safety.py tests/test_phase6_mcp.py
```

The integration test discovers eight tools from the official MCP client, verifies each input and
output schema, invokes all eight through `MCPToolExecutor`, and validates the nine trace entries
(discovery plus eight calls). The safety suite proves refusal without confirmation, signature and
expiry checks, exact action binding, idempotency, trace redaction, and no seed-file mutation. See
`docs/phase6-mcp-tools.md` for the tool catalog and manual behavior.

## Current API smoke test

With the backend running, execute:

```powershell
$body = @{
    employee_id = "E-1007"
    message = "Can I work remotely from Germany for six weeks?"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat `
    -ContentType application/json -Body $body
```

Verify a conditional outcome; exact citations `INT-5`, `INT-13`, `RWK-5`, and `SEC-8`; enriched
chunk metadata; and the eight-entry trace from discovery through compliance.

## Phase 7 workflow verification

Run the focused workflows, safety gates, and machine-readable evaluation:

```powershell
python -m pytest tests/test_phase7_workflows.py tests/test_phase7_safety.py `
  tests/test_phase7_evaluation.py
python scripts/evaluate_workflows.py
```

The suite repeats both primary workflows, verifies the expense backup, preserves PTO and ticket
fixtures, exercises the confirmation API, proves idempotency and token redaction, and tests missing
IDs, relative dates, unavailable tools, retry, insufficient evidence, and policy conflicts. See
`docs/phase7-workflows.md` for request bodies and the manual confirmation sequence.

## Evaluation contracts

The runtime Pydantic contracts live in `app/api/contracts.py`; gold-case models and semantic validation live in `app/evaluation`. The committed suite is `evaluation/gold_cases.json`.

After intentionally changing a contract, regenerate and verify the JSON Schemas:

```powershell
python scripts/export_contract_schemas.py
python scripts/export_contract_schemas.py --check
```

See `docs/data-contracts.md` before modifying schemas or gold expectations.

### Local container builds behind HTTPS inspection

CI and production use the Dockerfile's secure TLS defaults. The preferred local solution is to make the organization's root certificate available to Docker. For a disposable local verification build only, the Dockerfile also accepts explicit npm and pip trust arguments:

```powershell
docker build --build-arg NPM_CONFIG_STRICT_SSL=false --build-arg "PIP_TRUSTED_HOST=pypi.org files.pythonhosted.org" -t peopleops-assistant:local .
```

Do not use those overrides in CI or production.

The all-in-one validation script accepts the same local-only mode:

```powershell
$env:PEOPLEOPS_DOCKER_TLS_INSPECTION = "1"
.\scripts\check.ps1
```

## Definition of done

A change is complete only when its implementation, tests, documentation, and traceability row agree; local checks pass; and the committed state is reproducible from a clean checkout.
