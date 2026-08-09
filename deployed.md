# Deployment status

## Current status

PeopleOps Assistant is live on a free Render web service managed by the repository's Blueprint.
The Phase 8 deployment of commit `eff029f` passed Render's `/health` check on 2026-08-08 Pacific
time (2026-08-09 UTC). Public browser and API smoke tests proved the evidence-first workspace, all
four reproducible tasks, and the confirmation-gated synthetic ticket experience.

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

- root returned HTTP 200 and rendered the application shell;
- `/health` returned `status=ok`, `version=0.5.0`, `environment=production`, and MCP
  `status=ready` with eight discoverable tools serving the Phase 8 product interface;
- the hosted browser rendered all four demo tasks, selected-employee context, citation and tool
  inspectors, request/trace identifiers, and live component health without console errors;
- the production RAG component reported `phase5-hybrid-v2` ready with 12 policies, 169 sections,
  and 169 chunks;
- remote-work eligibility returned `status=completed`, `outcome=conditional`, four validated
  citations, eight traced MCP calls, and a non-empty trace ID for E-1007;
- PTO guidance returned `status=completed`, `outcome=draft_only`, two validated citations, and
  eight traced MCP calls for E-1021;
- expense compliance returned `status=completed`, `outcome=conditional`, three validated
  citations, and seven traced MCP calls for E-1014;
- the hosted confirmation dialog showed the exact sanitized preview with no create call; cancel
  closed the dialog while preserving a blocked pending action;
- the API confirmation sequence created a synthetic ticket only after explicit confirmation;
  replay returned the same ticket, and the signed token was neither rendered nor traced;
- the committed Phase 7 evaluation passed repeated primary workflows, expense compliance,
  clarification, unavailable-service, evidence-conflict, confirmation, idempotency, token-redaction,
  and seed-immutability cases;
- five frontend tests covered the workspace, task loading, cited evidence, confirmation-bound
  creation, and cancel-without-create; 74 backend tests passed at 90% coverage;
- [GitHub CI run 31295258826](https://github.com/quakfoolee-dotcom/PeopleOps/actions/runs/31295258826)
  passed frontend, backend, and production-container jobs;
- GitHub deployment `5815577672` and Render deploy `dep-d9s0cohsrm7s73atfn80` reported success for
  exact commit `eff029f8a099b0345635dcce83ee27b96bf20ee7`.

## Release procedure

Pushes to `main` deploy only after the linked GitHub checks pass because `render.yaml` sets
`autoDeployTrigger: checksPass`. After each runtime change, verify the public root, `/health`, and the
remote-work, PTO, expense, and confirmation-gated action paths. Record cold and warm response times
separately when a free instance has spun down.
