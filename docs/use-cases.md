# Use cases and acceptance criteria

All identifiers and records described here are synthetic.

Automated evaluations use the **demo policy as-of date 2026-09-01**, aligned with the policy corpus.
The authoritative prompts, expected evidence, tool constraints, outcomes, and safety behavior are
versioned in `evaluation/gold_cases.json`.

## UC-01: View system readiness

**Actor:** Developer or grader

**Precondition:** The FastAPI service is running.

**Action:** Open `/health`.

**Expected result:** HTTP 200 reports the application, 12-policy corpus, 169-section hybrid RAG
index, deterministic mock data, and MCP transport as ready. The provider reports `ready` after a
successful authenticated model probe, `not_configured` when deliberately disabled, or `error`
without exposing credentials.

This use case is implemented in Phase 1 and covered by automated tests.

## UC-02: International remote-work eligibility

**Prompt:** “I am employee E-1007 and live in British Columbia. Can I work from Germany for six weeks? Explain the approvals I need.”

**Implemented Phase 7 sequence:**

1. Validate and look up the synthetic employee.
2. Discover and validate the complete eight-tool suite through the official MCP client.
3. Invoke `lookup_employee_profile` and `search_policy_documents` through MCP.
4. Retrieve and validate exact international-work, remote-work, and security sections through the
   hybrid RAG-backed policy tool.
5. Run the deterministic compliance screen and produce conditional next steps with citations and a
   sanitized operational trace.

**Acceptance:** Real MCP calls appear in the operational trace; citations support each material
policy statement; unavailable tools or missing evidence never result in invented employee facts.
Missing identifiers or trip details clarify before tool use; unavailable tools, insufficient
evidence, or policy conflicts fail closed or escalate.

This workflow was implemented in Phase 4 and upgraded to hybrid retrieval in Phase 5. MCP,
orchestrator, API, RAG, and UI tests cover it.

Gold-case mapping: `EVAL-MULTI-001` and `EVAL-TOOL-001`.

## UC-03: PTO request guidance

**Prompt:** “I am employee E-1021. Can I take three PTO days next week? Check my balance and draft a message to my manager.”

**Implemented Phase 7 workflow:**

1. Clarify dates when “next week” is ambiguous relative to the fixed test date.
2. Look up the synthetic employee and PTO balance through MCP.
3. Retrieve PTO eligibility, notice, and approval sections.
4. Calculate requested working days and evaluate compliance.
5. Return a clearly labelled manager-message artifact with recipient, subject, readable body,
   `sent=false`, and `persisted=false`.

**Acceptance:** Balance data comes only from the structured-data tool; the answer distinguishes
eligibility from approval; the draft is rendered separately from guidance and exposes no send
action; no PTO record is changed.

Gold-case mapping: `EVAL-TOOL-002`; relative-date clarification is covered by `EVAL-AMB-001`.

## UC-04: Expense compliance backup

**Prompt:** “Can employee E-1014 be reimbursed for a CAD 900 home-office chair?”

**Implemented Phase 7 workflow:** Retrieve the employee role and location,
equipment and expense policies, applicable allowance, and approval rules; return a cited compliant,
conditional, or unsupported result. The ordinary CAD 500 cap and CAD 400 employee-paid remainder
for the E-1014/CAD 900 example are calculated by the compliance tool, not invented by the agent.

Gold-case mapping: `EVAL-MULTI-002` and `EVAL-TOOL-003`.

## UC-05: Confirmation-gated mock ticket

**Action:** Ask the assistant to create an HR ticket.

**Expected result:** The assistant gathers evidence, shows a preview, and asks for explicit
confirmation. No record is created before confirmation; repeated confirmation is handled
idempotently. Phase 7 sequences policy evidence, preview, the explicit-confirmation API, and the MCP
create tool while preserving exact action binding, expiry, redaction, and process-local mutation.
Phase 8 renders the exact preview in an accessible confirmation dialog, keeps cancellation blocked,
and reuses the original request binding after confirmation without exposing the signed token.

Gold-case mapping: `EVAL-TOOL-006` and `EVAL-SAFE-003`.

## UC-06: Validate and materialize synthetic data

**Actor:** Developer or grader

**Action:** Run `python scripts/validate_phase3_assets.py`.

**Expected result:** Validation reports 12 policies, 45 estimated pages, Markdown and PDF runtime formats, 30 employees, 6 locations, and 6 historical tickets. The command also builds and checks a temporary SQLite database without leaving a generated artifact.

**Optional action:** Add `--database mock_data/generated/peopleops.db` to retain a local SQLite copy. The committed JSON seed remains authoritative.

**Failure behavior:** A checksum mismatch, schema violation, missing reference, manager cycle, inconsistent snapshot date, future record, missing gold-case employee, or SQLite foreign-key error returns a non-zero exit code.

## Operational trace contract

The UI and `/chat` response expose request ID, selected MCP tool, sanitized arguments, summarized
tool result, retrieved policy IDs and sections, workflow status, clarification or escalation decision,
and final answer basis. They do not expose hidden chain-of-thought.

## UC-07: Reproduce workflows in the product workspace

**Actor:** Grader or reviewer

**Action:** Open the application, run the remote-work and PTO demo tasks, and inspect the result,
employee context, citations, tool trace, request ID, trace ID, and service health.

**Expected result:** Both workflows are reproducible without editing JSON or opening developer
tools. Citation and tool details reflect the live API response, responsive panels remain usable at
narrow widths, and no navigation or action control is a non-functional placeholder.

## UC-08: Verify and release an exact commit

**Actor:** Maintainer or automated release workflow

**Action:** Push a candidate commit to `main`, or run `Hosted smoke` manually with an expected SHA.

**Expected result:** Backend contracts, lint, corpus/index checks, MCP/workflow evaluations, frontend
tests/build, and a production-container startup smoke all pass. The explicit release gate succeeds;
Render deploys only after the linked checks pass; and the post-deploy job proves the public health
response matches the exact commit before completing a real read-only cited MCP workflow.

**Failure behavior:** A failed or skipped prerequisite fails the release gate. Version, environment,
commit, component, citation, trace, or decision drift fails smoke with no write-like action. Follow
the Phase 9 runbook to inspect evidence and roll back to the last verified immutable commit.

## UC-09: Generate a provider-backed grounded summary

**Actor:** Grader or reviewer

**Precondition:** OpenRouter is configured through Render environment variables and provider health
is ready.

**Action:** Run the E-1007 Germany workflow and inspect the response header and generation metadata.

**Expected result:** The response identifies `openrouter` and the resolved model, displays a concise
AI-generated summary with the complete verified citation set, then displays the unchanged verified
workflow result. The provider has no tool, RAG, data-store, or action access.

**Failure behavior:** A timeout, retry exhaustion, authentication/quota problem, invalid JSON,
unknown citation, omitted protected fact, or introduced identifier/number results in
`deterministic_fallback`; no partial model output is shown and the verified workflow answer remains
available.

## UC-10: Answer a general policy question

**Actor:** Employee, developer, or grader

**Prompt:** “How long does a newly eligible employee have to complete benefits enrollment?”

**Workflow:** Classify the bounded policy topic, discover MCP tools, run hybrid policy search,
retrieve exact section `POL-BEN-001 BEN-5`, validate the citation, and optionally synthesize a
provider summary above the unchanged verified answer. Do not retrieve an employee profile or
benefits record for a general question.

**Acceptance:** The response says 31 calendar days, distinguishes later open-enrollment or
qualifying-life-event changes, cites only `BEN-5`, and traces only discovery, policy search, and the
exact-section call.

The same policy workflow handles the other gold-suite policy topics, employee-specific benefits and
onboarding lookups, cited leave clarification, manager escalation, and cited privacy refusal without
adding MCP tools or allowing direct agent access to RAG or synthetic data.
