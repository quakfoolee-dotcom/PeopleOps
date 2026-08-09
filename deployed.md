# Deployment status

## Current status

PeopleOps Assistant version `0.7.0` is live on a free Render web service managed by the repository's
Blueprint. The Phase 9 release of exact commit `885b7f242c21635a97e2c64be704c1d16fc34943`
passed the pre-deployment release gate, Render health check, exact-commit deployment status, and
automated post-deployment public smoke on 2026-08-08 Pacific time (2026-08-09 UTC).

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

- [GitHub CI run 31298687350](https://github.com/quakfoolee-dotcom/PeopleOps/actions/runs/31298687350)
  passed backend, frontend, production-container startup/workflow smoke, evidence upload, and the
  explicit release gate;
- all 82 backend tests passed at 90.49% coverage; six frontend tests and the strict TypeScript/Vite
  production build passed, including five consecutive local runs of the formerly timing-sensitive
  confirmation-focus test;
- GitHub deployment `5816151462` reported success for exact commit
  `885b7f242c21635a97e2c64be704c1d16fc34943` in environment
  `main - peopleops-assistant-demo`;
- [hosted smoke run 31298780994](https://github.com/quakfoolee-dotcom/PeopleOps/actions/runs/31298780994)
  checked out that exact commit, passed the public release contract, and retained artifact
  `hosted-smoke-31298780994` for 30 days;
- `/health` returned `status=ok`, `version=0.7.0`, `environment=production`, full release SHA
  `885b7f242c21635a97e2c64be704c1d16fc34943`, and ready application, corpus, RAG, MCP, and mock-data
  components;
- hosted health/wake, root, and chat timings were 273 ms, 264 ms, and 2,082 ms respectively;
- the read-only E-1007 Germany workflow returned a conditional outcome with exact sections `INT-5`,
  `INT-13`, `RWK-5`, and `SEC-8`, plus eight MCP operations and non-empty request/trace IDs;
- dependency configuration validation passed; all seven policy-reconciliation jobs succeeded, and
  incompatible bundled major/runtime-line update PRs were automatically closed;
- a separate Windows native health request independently returned the expected version, full release
  SHA, and component state. The Python duplicate smoke was blocked before HTTP by the managed
  network's non-standard inspection CA, while the clean GitHub-hosted path passed with normal TLS
  verification.

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
