# Deployment status

## Current production release

PeopleOps Assistant version `1.0.0` is live on a free Render web service managed by the repository
Blueprint. As verified on **2026-08-09 Pacific time**, `/health.release_sha` reports exact release
`2300463a40ff49b87d248e6a612976a82e62ec2f`. Production reports healthy application, 12-policy
corpus, 169-chunk RAG index, eight-tool MCP service, 30-record synthetic employee data, and a ready
OpenRouter provider.

Production uses `LLM_PROVIDER=openrouter` with the zero-cost `openrouter/free` route. The owner-held
credential is stored only as a masked Render environment variable. GitHub repository variable
`PRODUCTION_LLM_PROVIDER=openrouter` makes deployment-triggered smoke require ready provider health
and an accepted grounded provider response. `/health.release_sha` is the authoritative identity for
the currently served revision.

## Hosted endpoints

- Application: <https://peopleops-assistant-demo.onrender.com>
- Health: <https://peopleops-assistant-demo.onrender.com/health>
- API documentation: <https://peopleops-assistant-demo.onrender.com/docs>
- Deployment provider: Render, free Docker web service, Blueprint-managed from `main`

## Current verified evidence

- [CI run 31332899182](https://github.com/quakfoolee-dotcom/PeopleOps/actions/runs/31332899182)
  passed the backend, evaluation, frontend, production-container workflow smoke, evidence upload,
  and release gate for exact release `2300463a40ff49b87d248e6a612976a82e62ec2f`;
- [deployment-triggered hosted smoke 31333011120](https://github.com/quakfoolee-dotcom/PeopleOps/actions/runs/31333011120)
  passed exact-release identity, public health, root interface, citations, MCP trace, and provider
  requirements;
- public health reports `status=ok`, `version=1.0.0`, `environment=production`, the full release
  SHA, and ready application, corpus, RAG, MCP, mock-data, and OpenRouter components;
- three additional generic, non-identifying, read-only workflows all preserved the exact expected
  outcome, citations, required tools, and no-write boundary. OpenRouter produced one accepted
  grounded summary and two requests returned the unchanged verified fallback: 33.33% observed
  provider acceptance, 100% workflow integrity, and 5,663 ms p50 / 25,565 ms p95 end-to-end latency;
- no employee-specific production prompt and no write-like production operation was used for that
  supplementary provider sample.

The branch containing the latest Score-5 evidence and documentation is a release candidate until
its pull request is reviewed and merged. This document deliberately does not represent local or PR
changes as already deployed.

## Cold-start plan

Render's free web service can spin down after inactivity and may take about one minute to wake. The
committed policy corpus and synthetic records are read-only, so Render's ephemeral filesystem is
safe for this demonstration. The current local deterministic-provider evaluation records a 683 ms
first-process primary request and 132 ms p50 / 204 ms p95 across 20 warm gold cases. These local
measurements are not hosted-service promises, and a Render health check before deployment success is
not claimed as a true spun-down cold start.

## Release and rollback procedure

Two automated controls protect production:

1. `CI / Release gate` accepts a candidate only after backend, evaluation, frontend, and
   production-container startup/workflow checks pass. Render's `autoDeployTrigger: checksPass` then
   permits deployment from `main`.
2. A successful Render `deployment_status` event starts `Hosted smoke` against the exact deployment
   SHA. It verifies release identity, component health, the root interface, exact citations, and a
   read-only MCP workflow while retaining JSON evidence. Provider-required smoke allows up to three
   attempts only for the application's verified deterministic fallback; structural or evidence
   drift fails immediately.

The smoke runner allows a bounded 240 seconds for free-tier wake-up and records wake time separately
from endpoint latency. Rollback targets the last immutable commit with both a successful release gate
and hosted-smoke artifact. Use Render's rollback control, rerun `Hosted smoke` with that SHA, and use
a normal `git revert` for a source rollback. Do not force-deploy a failed commit or rewrite `main`.
The full operator procedure is in `docs/phase9-cicd-deployment.md`.
