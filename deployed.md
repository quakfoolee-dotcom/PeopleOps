# Deployment status

## Current status

PeopleOps Assistant is live on a free Render web service managed by the repository's Blueprint.
The Phase 6 deployment of commit `32606d5` passed Render's `/health` check on 2026-08-08. Public
browser and API smoke tests then proved the application shell, production eight-tool MCP health
response, and complete cited `/chat` workflow.

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

- root returned HTTP 200 and rendered the Phase 6 interface;
- `/health` returned `status=ok`, `version=0.3.0`, `environment=production`, and MCP
  `status=ready` with eight discoverable Phase 6 tools;
- the production RAG component reported `phase5-hybrid-v2` ready with 12 policies, 169 sections,
  and 169 chunks;
- `/chat` returned `status=completed` and `outcome=conditional` for E-1007;
- the response contained eight validated policy citations;
- the operational trace recorded discovery of all eight MCP tools, employee lookup, and policy
  search without exposing confirmation tokens or sensitive arguments;
- the committed Phase 6 evaluation passed discovery, input/output schemas, successful invocation
  of all eight tools, confirmation rejection, token redaction, idempotency, and seed immutability;
- GitHub CI run 31291627825 passed backend, frontend, and production-container jobs before the
  Phase 6 deployment;
- GitHub deployment `5814967236` and Render deploy `dep-d9rusdr7uimc73bb9o10` reported success for
  commit `32606d53abd3118ac37ccb3ca84a9824a583a658`.

## Release procedure

Pushes to `main` deploy only after the linked GitHub checks pass because `render.yaml` sets
`autoDeployTrigger: checksPass`. After each runtime change, verify the public root, `/health`, and the
E-1007 preset. Record cold and warm response times separately when a free instance has spun down.
