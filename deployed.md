# Deployment status

## Current status

PeopleOps Assistant version `0.8.0` is live on a free Render web service managed by the repository's
Blueprint. The LLM-provider implementation source commit
`ef7148bae4c30cd33a944bd8b7d9689e041df447` passed the pre-deployment release gate, Render health
check, exact-commit deployment status, and automated post-deployment public smoke on 2026-08-09
Pacific time. `/health.release_sha` remains the authoritative identity for the currently served
documentation or application revision.

The provider boundary is deployed, but production intentionally remains in verified deterministic
mode until the owner adds `OPENROUTER_API_KEY` and `LLM_PROVIDER=openrouter` in Render. Health reports
this state as `llm_provider.status=not_configured`; no secret is stored in the repository.

## Hosted endpoints

- Application: <https://peopleops-assistant-demo.onrender.com>
- Health: <https://peopleops-assistant-demo.onrender.com/health>
- API documentation: <https://peopleops-assistant-demo.onrender.com/docs>
- Deployment provider: Render, free Docker web service, Blueprint-managed from `main`

## Cold-start plan

Render's free web service can spin down after 15 minutes without inbound traffic and can take about
one minute to wake. The committed policy corpus and synthetic records are read-only, so Render's
ephemeral filesystem is safe for this phase. Phase 10 will measure cold and warm latency separately.

## Verified production evidence

- [GitHub CI run 31300869320](https://github.com/quakfoolee-dotcom/PeopleOps/actions/runs/31300869320)
  passed backend, frontend, provider-boundary, production-container startup/workflow smoke, evidence
  upload, and the explicit release gate;
- all 92 backend tests passed at 89.74% coverage; six frontend tests and the strict TypeScript/Vite
  production build passed;
- [hosted smoke run 31300897702](https://github.com/quakfoolee-dotcom/PeopleOps/actions/runs/31300897702)
  checked the exact release, passed the public release contract, and retained its JSON evidence for
  30 days;
- for the implementation source release, `/health` returned `status=ok`, `version=0.8.0`,
  `environment=production`, full release SHA
  `ef7148bae4c30cd33a944bd8b7d9689e041df447`, and ready application, corpus, RAG, MCP, and mock-data
  components, plus the truthful `not_configured` provider state;
- the read-only E-1007 Germany workflow returned a conditional outcome with exact sections `INT-5`,
  `INT-13`, `RWK-5`, and `SEC-8`, plus eight MCP operations, non-empty request/trace IDs, and
  `generation.mode=deterministic` while the production secret is absent;
- local browser QA exercised the configured deterministic provider adapter and displayed its model,
  separated AI summary, unchanged verified result, four citations, and eight-operation MCP trace with
  no console errors;
- a separate Windows native production contract check independently returned the expected version,
  full release SHA, component state, citations, and trace. The Python duplicate smoke was blocked
  before HTTP by the managed network's non-standard inspection CA, while the clean GitHub-hosted path
  passed with normal TLS verification.

## Release procedure

Phase 9 replaces the former manual-only smoke procedure with two automated controls:

1. `CI / Release gate` accepts a candidate only after backend, frontend, and production-container
   startup/workflow checks pass. Render's `autoDeployTrigger: checksPass` then permits deployment.
2. A successful Render `deployment_status` event starts `Hosted smoke` against the exact deployment
   SHA. It verifies release identity, component health, the root interface, exact citations, and a
   real read-only MCP workflow while retaining JSON evidence.

`/health.release_sha` comes from Render's runtime commit metadata and must equal the GitHub deployment
SHA. The smoke runner allows a bounded 240 seconds for a free-tier cold start and records the actual
wake time separately from endpoint latencies.

Rollback targets the last immutable commit with both a successful release gate and hosted-smoke
artifact. Use Render's rollback control, rerun `Hosted smoke` with that SHA, and use a normal
`git revert` for a source rollback. Do not force-deploy a failed commit or rewrite `main`. The full
operator procedure is in `docs/phase9-cicd-deployment.md`.
