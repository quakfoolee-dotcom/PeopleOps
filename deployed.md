# Deployment status

## Current status

PeopleOps Assistant is live on a free Render web service managed by the repository's Blueprint.
The Phase 7 deployment of commit `a96723f` passed Render's `/health` check on 2026-08-08 Pacific
time (2026-08-09 UTC). Public API smoke tests then proved all three bounded guidance workflows and
the confirmation-gated synthetic ticket action against the deployed service.

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
- `/health` returned `status=ok`, `version=0.4.0`, `environment=production`, and MCP
  `status=ready` with eight discoverable tools serving Phase 7 workflows;
- the production RAG component reported `phase5-hybrid-v2` ready with 12 policies, 169 sections,
  and 169 chunks;
- remote-work eligibility returned `status=completed`, `outcome=conditional`, four validated
  citations, and eight traced MCP calls for E-1007;
- PTO guidance returned `status=completed`, `outcome=draft_only`, two validated citations, and
  eight traced MCP calls for E-1021;
- expense compliance returned `status=completed`, `outcome=conditional`, three validated
  citations, and seven traced MCP calls for E-1014;
- a mock HR ticket first returned `awaiting_confirmation` with no create call, then created
  `TKT-9001` only after explicit API confirmation; replay returned the same ticket, and the signed
  confirmation token was absent from the operational trace;
- the committed Phase 7 evaluation passed repeated primary workflows, expense compliance,
  clarification, unavailable-service, evidence-conflict, confirmation, idempotency, token-redaction,
  and seed-immutability cases;
- [GitHub CI run 31293879728](https://github.com/quakfoolee-dotcom/PeopleOps/actions/runs/31293879728)
  passed backend, frontend, and production-container jobs, including the explicit Phase 7 workflow
  evaluation and all 74 backend tests;
- GitHub deployment `5815347459` and Render deploy `dep-d9rvqhoae00c73abgst0` reported success for
  exact commit `a96723ffc944028d01bbf8dfb2238ddef6e12910`.

## Release procedure

Pushes to `main` deploy only after the linked GitHub checks pass because `render.yaml` sets
`autoDeployTrigger: checksPass`. After each runtime change, verify the public root, `/health`, and the
remote-work, PTO, expense, and confirmation-gated action paths. Record cold and warm response times
separately when a free instance has spun down.
