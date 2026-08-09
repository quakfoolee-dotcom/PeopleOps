# Deployment status

## Current status

PeopleOps Assistant is live on a free Render web service managed by the repository's Blueprint.
The Phase 8.2 structured-result deployment of commit `68c24ed` passed Render's `/health` check on
2026-08-08 Pacific time (2026-08-09 UTC). Public browser and API smoke tests proved the
evidence-first workspace, structured workflow decisions, the real MCP-backed email-draft action,
all four reproducible tasks, and the confirmation-gated synthetic ticket experience.

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
- `/health` returned `status=ok`, `version=0.6.0`, `environment=production`, and MCP
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
- the hosted result card separately rendered `Conditionally eligible`, 42 calendar/30 business
  days, `International exceptional`, seven required approvals, exact-date clarification, and five
  evidence-derived next steps;
- **Draft PeopleOps email** reran the bounded remote-work workflow and finished with
  `outcome=draft_only`, nine traced MCP operations ending in `draft_hr_email`, and explicit
  `sent=false` and `persisted=false` evidence;
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
- six frontend tests covered the workspace, structured decisions, the real draft action, cited
  evidence, confirmation-bound creation, and cancel-without-create; 75 backend tests passed at
  90.48% coverage;
- [GitHub CI run 31297341809](https://github.com/quakfoolee-dotcom/PeopleOps/actions/runs/31297341809)
  passed frontend, backend, and production-container jobs;
- GitHub deployment `5815920698` and Render deploy `dep-d9s185mq1p3s73fd69tg` reported success for
  exact commit `68c24ed58af99988fe521e0c7d4f45090bb9d9cc`.

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
