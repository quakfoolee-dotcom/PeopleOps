# Deployment status

## Current status

PeopleOps Assistant is live on a free Render web service managed by the repository's Blueprint.
The initial deployment of commit `8582fa3` passed Render's `/health` check on 2026-08-08. Public
browser and API smoke tests then proved the application shell, production health response, and
complete Phase 4 `/chat` workflow.

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

- root returned HTTP 200 and rendered the Phase 4 interface;
- `/health` returned `status=ok`, `environment=production`, and MCP `status=ready`;
- `/chat` returned `status=completed` and `outcome=conditional` for E-1007;
- citations were `INT-4`, `INT-5`, `INT-13`, and `RWK-5`;
- the operational trace recorded discovery, employee lookup, and policy search;
- GitHub CI run 31285649773 passed backend, frontend, and production-container jobs before the
  initial deployment.

## Release procedure

Pushes to `main` deploy only after the linked GitHub checks pass because `render.yaml` sets
`autoDeployTrigger: checksPass`. After each runtime change, verify the public root, `/health`, and the
E-1007 preset. Record cold and warm response times separately when a free instance has spun down.
