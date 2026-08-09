# Deployment status

## Current status

PeopleOps Assistant is live on a free Render web service managed by the repository's Blueprint.
The Phase 8.1 readability deployment of commit `2c8d4fd` passed Render's `/health` check on
2026-08-08 Pacific time (2026-08-09 UTC). Public browser and API smoke tests proved the
evidence-first workspace, all four reproducible tasks, the confirmation-gated synthetic ticket
experience, and the corrected citation and tool-trace typography.

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
- `/health` returned `status=ok`, `version=0.5.1`, `environment=production`, and MCP
  `status=ready` with eight discoverable tools serving the Phase 8 product interface;
- the hosted readability check measured citation body text at 13 px and tool names and trace
  results at 12 px, with no horizontal page overflow; citation previews now normalize Markdown
  table separators and provide an expandable full cited snippet;
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
- [GitHub CI run 31296254933](https://github.com/quakfoolee-dotcom/PeopleOps/actions/runs/31296254933)
  passed frontend, backend, and production-container jobs;
- GitHub deployment `5815737918` and Render deploy `dep-d9s0ptrbc2fs73b0ccp0` reported success for
  exact commit `2c8d4fd759f3d20e9e60d167a3a5f805178bc315`.

## Release procedure

Pushes to `main` deploy only after the linked GitHub checks pass because `render.yaml` sets
`autoDeployTrigger: checksPass`. After each runtime change, verify the public root, `/health`, and the
remote-work, PTO, expense, and confirmation-gated action paths. Record cold and warm response times
separately when a free instance has spun down.
