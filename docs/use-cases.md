# Use cases and acceptance criteria

All identifiers and records described here are synthetic.

Automated evaluations use the fixed as-of date **2026-08-17**. The authoritative prompts, expected evidence, tool constraints, outcomes, and safety behavior are versioned in `evaluation/gold_cases.json`.

## UC-01: View system readiness

**Actor:** Developer or grader

**Precondition:** The FastAPI service is running.

**Action:** Open `/health`.

**Expected result:** HTTP 200 reports the application and 12-policy corpus as ready, while unfinished RAG, MCP, data, and provider components are explicitly marked planned or not configured.

This use case is implemented in Phase 1 and covered by automated tests.

## UC-02: International remote-work eligibility

**Prompt:** “I am employee E-1007 and live in British Columbia. Can I work from Germany for six weeks? Explain the approvals I need.”

**Required future sequence:**

1. Validate and look up the synthetic employee.
2. Retrieve remote-work, international-work, and security policies.
3. Retrieve exact sections when required.
4. Evaluate deterministic policy compliance.
5. Produce conditional next steps with claim-level citations.
6. Offer a draft request without sending or recording anything.

**Acceptance:** Real MCP calls appear in the operational trace; citations support each material policy statement; unavailable tools or missing evidence never result in invented employee facts.

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

## Operational trace contract

The UI and `/chat` response will expose request ID, selected MCP tool, sanitized arguments, summarized tool result, retrieved policy IDs and sections, workflow status, clarification or escalation decision, and final answer basis. It will not expose hidden chain-of-thought.
