# Deployment status

## Current status

PeopleOps Assistant is live on a free Render web service managed by the repository's Blueprint.
The Phase 5 deployment of commit `3f18d1a` passed Render's `/health` check on 2026-08-08. Public
browser and API smoke tests then proved the application shell, production hybrid RAG health
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

- root returned HTTP 200 and rendered the Phase 5 interface;
- `/health` returned `status=ok`, `version=0.2.0`, `environment=production`, and MCP
  `status=ready`;
- the production RAG component reported `phase5-hybrid-v2` ready with 12 policies, 169 sections,
  and 169 chunks;
- `/chat` returned `status=completed` and `outcome=conditional` for E-1007;
- the eight validated citation sections were `INT-9`, `RWK-5`, `SEC-8`, `INT-13`, `INT-3`,
  `INT-1`, `INT-5`, and `RWK-1`;
- the operational trace recorded discovery, employee lookup, and policy search;
- GitHub CI run 31288806706 passed backend, frontend, and production-container jobs before the
  Phase 5 deployment.

## Release procedure

Pushes to `main` deploy only after the linked GitHub checks pass because `render.yaml` sets
`autoDeployTrigger: checksPass`. After each runtime change, verify the public root, `/health`, and the
E-1007 preset. Record cold and warm response times separately when a free instance has spun down.
