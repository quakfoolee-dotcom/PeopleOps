# Use cases and acceptance criteria

All identifiers and records described here are synthetic.

Automated evaluations use the fixed as-of date **2026-09-01**, aligned with the policy corpus. The authoritative prompts, expected evidence, tool constraints, outcomes, and safety behavior are versioned in `evaluation/gold_cases.json`.

## UC-01: View system readiness

**Actor:** Developer or grader

**Precondition:** The FastAPI service is running.

**Action:** Open `/health`.

**Expected result:** HTTP 200 reports the application, 12-policy corpus, deterministic mock data,
and Phase 4 MCP transport as ready, while unfinished RAG and provider components are explicitly
marked planned or not configured.

This use case is implemented in Phase 1 and covered by automated tests.

## UC-02: International remote-work eligibility

**Prompt:** “I am employee E-1007 and live in British Columbia. Can I work from Germany for six weeks? Explain the approvals I need.”

**Phase 4 sequence:**

1. Validate and look up the synthetic employee.
2. Discover both live tools through the official MCP client.
3. Invoke `lookup_employee_profile` and `search_policy_documents` through MCP.
4. Retrieve exact remote-work and international-work sections.
5. Produce conditional next steps with citations and a sanitized operational trace.

**Acceptance:** Real MCP calls appear in the operational trace; citations support each material
policy statement; unavailable tools or missing evidence never result in invented employee facts.
Draft generation and deeper compliance evaluation remain Phase 7 work.

This use case is implemented in Phase 4 and covered by MCP, orchestrator, API, and UI tests.

Gold-case mapping: `EVAL-MULTI-001` and `EVAL-TOOL-001`.

## UC-03: PTO request guidance

**Prompt:** “I am employee E-1021. Can I take three PTO days next week? Check my balance and draft a message to my manager.”

**Required future sequence:**

1. Clarify dates when “next week” is ambiguous relative to the fixed test date.
2. Look up the synthetic employee and PTO balance through MCP.
3. Retrieve PTO eligibility, notice, and approval sections.
4. Calculate requested working days and evaluate compliance.
5. Return a clearly labelled, non-persistent manager-message draft.

**Acceptance:** Balance data comes only from the structured-data tool; the answer distinguishes eligibility from approval; no PTO record is changed.

Gold-case mapping: `EVAL-TOOL-002`; relative-date clarification is covered by `EVAL-AMB-001`.

## UC-04: Expense compliance backup

**Prompt:** “Can employee E-1014 be reimbursed for a CAD 900 home-office chair?”

**Required future sequence:** Retrieve the employee role and location, equipment and expense policies, applicable allowance, and approval rules; return a cited compliant, conditional, or unsupported result.

Gold-case mapping: `EVAL-MULTI-002` and `EVAL-TOOL-003`.

## UC-05: Confirmation-gated mock ticket

**Action:** Ask the assistant to create an HR ticket.

**Expected result:** The assistant gathers evidence, shows a preview, and asks for explicit confirmation. No record is created before confirmation; repeated confirmation is handled idempotently.

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
