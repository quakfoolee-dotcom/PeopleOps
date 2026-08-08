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

## Configuration

Copy `.env.example` to `.env`. Provider keys are intentionally absent from the example. Future provider-specific keys must be read from the environment and must never be returned by `/health`.

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
