# Deployment status

## Current status

PeopleOps Assistant version `1.0.0` is live on a free Render web service managed by the repository's
Blueprint. Phase 10 functional release `ad65bee837fc5a28cad940a1b2d48e1cef72b231` passed the pre-deployment
release gate, Render health check, exact-commit deployment status, OpenRouter-required
deployment-triggered smoke, and an independent warm public smoke on 2026-08-09 Pacific time.
`/health.release_sha` remains the authoritative identity for the currently served revision.

Production uses `LLM_PROVIDER=openrouter` with the zero-cost `openrouter/free` route. The owner-held
credential is stored only as a masked Render environment variable. GitHub repository variable
`PRODUCTION_LLM_PROVIDER=openrouter` makes every later deployment-triggered smoke require ready
provider health and an accepted grounded provider response.

## Hosted endpoints

- Application: <https://peopleops-assistant-demo.onrender.com>
- Health: <https://peopleops-assistant-demo.onrender.com/health>
- API documentation: <https://peopleops-assistant-demo.onrender.com/docs>
- Deployment provider: Render, free Docker web service, Blueprint-managed from `main`

## Cold-start plan

Render's free web service can spin down after inactivity and may take about one minute to wake. The
committed policy corpus and synthetic records are read-only, so Render's ephemeral filesystem is
safe for this demonstration. Phase 10 records a 1,045 ms local first-process request, 226 ms p50 and
363 ms p95 across 20 local warm cases, plus separate deployment-triggered and warm hosted samples.
Render health-checks a release before declaring deployment success, so that sample is not claimed
as a true spun-down cold start.

## Verified production evidence

- [GitHub CI run 31328913632](https://github.com/quakfoolee-dotcom/PeopleOps/actions/runs/31328913632)
  passed backend, Phase 10 gold gates, frontend, production-container startup/workflow smoke,
  evidence upload, and the explicit release gate;
- all 99 backend tests passed above the 85% coverage gate; six frontend tests and the strict
  TypeScript/Vite production build passed;
- [deployment-triggered hosted smoke 31329027152](https://github.com/quakfoolee-dotcom/PeopleOps/actions/runs/31329027152)
  and [warm hosted smoke 31329415784](https://github.com/quakfoolee-dotcom/PeopleOps/actions/runs/31329415784)
  both checked the exact release, passed the public provider contract, and retained JSON evidence;
- `/health` returned `status=ok`, `version=1.0.0`, `environment=production`, full Phase 10 release
  SHA, ready application/corpus/RAG/MCP/mock-data components, and authenticated `openrouter` health;
- the read-only E-1007 Germany workflow returned a conditional outcome with exact sections `INT-5`,
  `INT-13`, `RWK-5`, and `SEC-8`, plus eight MCP operations, non-empty request/trace IDs, and
  `generation.mode=provider`;
- OpenRouter resolved `openrouter/free` to `google/gemma-4-26b-a4b-it:free`; every displayed provider
  summary passed protected-fact, identifier, number, and exact-citation validation;
- the deployment-triggered sample recorded two safe fallbacks before a third accepted attempt and
  115,357 ms total chat time; the immediate warm sample was accepted on its first attempt in
  16,979 ms, with 393 ms health and 147 ms root responses;
- unauthenticated GET checks returned HTTP 200 for the repository, application, health, and API
  documentation links; the clean GitHub-hosted smoke used normal TLS verification and retained
  provider-attempt evidence.

## Release procedure

Phase 9 replaces the former manual-only smoke procedure with two automated controls:

1. `CI / Release gate` accepts a candidate only after backend, frontend, and production-container
   startup/workflow checks pass. Render's `autoDeployTrigger: checksPass` then permits deployment.
2. A successful Render `deployment_status` event starts `Hosted smoke` against the exact deployment
   SHA. It verifies release identity, component health, the root interface, exact citations, and a
   real read-only MCP workflow while retaining JSON evidence. When production requires a provider,
   the smoke permits up to three attempts but retries only the application's verified deterministic
   fallback; all structural or evidence drift fails immediately.

`/health.release_sha` comes from Render's runtime commit metadata and must equal the GitHub deployment
SHA. The smoke runner allows a bounded 240 seconds for a free-tier cold start and records the actual
wake time separately from endpoint latencies.

Rollback targets the last immutable commit with both a successful release gate and hosted-smoke
artifact. Use Render's rollback control, rerun `Hosted smoke` with that SHA, and use a normal
`git revert` for a source rollback. Do not force-deploy a failed commit or rewrite `main`. The full
operator procedure is in `docs/phase9-cicd-deployment.md`.
