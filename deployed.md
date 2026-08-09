# Deployment status

## Current status

PeopleOps Assistant version `0.8.0` is live on a free Render web service managed by the repository's
Blueprint. The production-provider smoke-hardening source commit
`9f0a5cda160a0c9a3702bd3632706f158a582b81` passed the pre-deployment release gate, Render health
check, exact-commit deployment status, and OpenRouter-required post-deployment public smoke on
2026-08-09 Pacific time. `/health.release_sha` remains the authoritative identity for the currently
served documentation or application revision.

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

Render's free web service can spin down after 15 minutes without inbound traffic and can take about
one minute to wake. The committed policy corpus and synthetic records are read-only, so Render's
ephemeral filesystem is safe for this phase. Phase 10 will measure cold and warm latency separately.

## Verified production evidence

- [GitHub CI run 31304936392](https://github.com/quakfoolee-dotcom/PeopleOps/actions/runs/31304936392)
  passed backend, frontend, production-container startup/workflow smoke, evidence upload, and the
  explicit release gate;
- all 96 backend tests passed at 89.74% coverage; six frontend tests and the strict TypeScript/Vite
  production build passed;
- [OpenRouter-required hosted smoke run 31305030455](https://github.com/quakfoolee-dotcom/PeopleOps/actions/runs/31305030455)
  checked the exact release, passed the public provider contract, and retained its JSON evidence for
  30 days;
- for the smoke-hardening source release, `/health` returned `status=ok`, `version=0.8.0`,
  `environment=production`, full release SHA
  `9f0a5cda160a0c9a3702bd3632706f158a582b81`, ready application/corpus/RAG/MCP/mock-data components,
  and authenticated `openrouter` provider health;
- the read-only E-1007 Germany workflow returned a conditional outcome with exact sections `INT-5`,
  `INT-13`, `RWK-5`, and `SEC-8`, plus eight MCP operations, non-empty request/trace IDs, and
  `generation.mode=provider`;
- OpenRouter resolved `openrouter/free` to `google/gemma-4-26b-a4b-it:free`; the provider summary
  passed protected-fact, identifier, number, and exact-citation validation in 25,727 ms;
- retained evidence recorded one accepted provider attempt, a 27,454 ms end-to-end chat request,
  165 ms health response, 54 ms root response, and no fallback attempt;
- production browser QA displayed the OpenRouter/resolved-model badge, separated AI summary,
  unchanged verified result, four citations, and eight-operation MCP trace with no console errors;
- a separate Windows native production contract check independently returned the expected version,
  full release SHA, provider state, citations, and trace. The clean GitHub-hosted path passed with
  normal TLS verification and retained provider-attempt evidence.

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
