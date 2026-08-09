# Phase 9 CI/CD and deployment operations

## Outcome

Phase 9 turns the existing build pipeline into an evidence-producing release control. A candidate
cannot reach Render until backend, frontend, and production-container checks pass. A successful
Render deployment then receives an independent public smoke test tied to its exact commit.

## Pre-deployment controls

The `CI` workflow runs on pushes to `main`, pull requests, and manual dispatches. It uses read-only
repository permissions, concurrency cancellation for superseded candidates, job timeouts, and
immutable full-SHA pins for third-party Actions.

1. **Backend quality and contracts** runs lint, schema drift, corpus/data validation, RAG index
   drift, MCP and workflow evaluations, all tests, and the 85% coverage floor. JUnit and coverage XML
   are retained for 14 days.
2. **Frontend test and production build** uses the lockfile with `npm ci`, runs the component suite,
   performs strict TypeScript validation, and creates the Vite production bundle.
3. **Container startup and workflow smoke** builds the actual Dockerfile, injects the candidate SHA,
   starts the container with the deterministic CI provider, waits for health, and runs the E-1007
   Germany workflow. It requires ready provider health and provider-mode grounded synthesis. Its JSON evidence is
   retained for 14 days; container logs are emitted on failure.
4. **Release gate** fails unless every prerequisite job succeeded. Render's Blueprint uses
   `autoDeployTrigger: checksPass`, so a failed candidate is not deployed.

Dependabot opens grouped weekly minor/patch maintenance updates for GitHub Actions, Python, and npm,
plus patch updates for Docker. Major package updates and Python/Node base-image line changes remain
deliberate migration work; security updates are not suppressed by this version-update policy. Action
references remain pinned to immutable full SHAs even when the readable version comment is updated.

## Smoke contract

`scripts/smoke_deployment.py` uses only the Python standard library and performs four checks:

1. retry `/health` until the cold-start deadline, requiring `status=ok`, expected version,
   environment, exact commit, and ready application/corpus/RAG/MCP/mock-data components;
2. verify `/` identifies PeopleOps Assistant;
3. submit a read-only E-1007 six-week Germany question to `/chat`;
4. require the conditional decision, sections `INT-5`, `INT-13`, `RWK-5`, `SEC-8`, eight traced MCP
   operations from discovery through compliance, generation metadata, and no pending write action.

The emitted JSON records timestamps, wake and request latency, request/trace IDs, citations, tool
count, and outcome. Validation functions are unit tested, including commit and citation drift.

## Hosted verification

Render reports deployments to GitHub as environment `main - peopleops-assistant-demo`. A successful
`deployment_status` event starts `Hosted smoke`, checks out that deployment's exact SHA, and applies
the same smoke contract to `https://peopleops-assistant-demo.onrender.com`. Evidence is retained for
30 days. The 240-second deadline accommodates the free service's cold start but remains bounded.

For a manual recheck, open **Actions → Hosted smoke → Run workflow**. Normally leave `expected_sha`
blank to check the selected branch commit; enter an exact 40-character SHA when auditing a known
deployment. After the production secret is configured, enter `openrouter` under
`expected_llm_provider` to require authenticated health and actual provider synthesis. Locally, use:

```powershell
.\scripts\smoke_test_api.ps1 `
  -BaseUrl "https://peopleops-assistant-demo.onrender.com" `
  -ExpectedEnvironment production `
  -ExpectedReleaseSha "<deployed-sha>" `
  -ExpectedLlmProvider openrouter
```

## Failure triage

1. Open the failed Actions job and download its backend or smoke artifact.
2. If backend/frontend failed, fix the candidate; do not manually deploy it.
3. If container startup failed, inspect the captured container logs and reproduce with Docker.
4. If hosted smoke reports a SHA mismatch, compare `/health.release_sha`, the GitHub deployment SHA,
   and the Render event before retrying. Never accept a response from a previous release.
5. If only cold start timed out, inspect Render events/logs and retry after the service is healthy.
6. If contract assertions failed, treat the release as unverified even when `/health` is HTTP 200.

## Rollback

Rollback targets the last commit that has both a successful `Release gate` and successful `Hosted
smoke` artifact. In Render, select that successful deploy and choose **Rollback**. Do not choose an
arbitrary build or force-deploy a commit whose CI failed. After rollback completes, manually run
`Hosted smoke` with the rollback commit SHA and record the successful run in `deployed.md`.

Source rollback uses a normal `git revert` commit on `main`, preserving history and re-running every
gate. Do not rewrite `main`. A rollback is complete only when `/health.release_sha` matches the chosen
commit and the read-only hosted workflow passes.

## Release checklist

- CI `Release gate` is successful for the candidate SHA.
- Render deployment reports success for the same SHA.
- Hosted smoke is successful and its artifact is retained.
- Public `/health` reports version, production environment, and the full candidate SHA.
- `deployed.md` records the version, commit, CI run, deployment, hosted smoke run, and latency.
- No secrets, confirmation proof, or real employee data appear in artifacts or logs.
