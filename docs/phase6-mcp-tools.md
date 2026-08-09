# Phase 6 MCP tool suite

Phase 6 implements the complete eight-tool contract behind the official MCP client/server boundary.
The agent layer does not import the structured store, RAG implementation, tool functions, or action
store directly. The current `/chat` workflow remains intentionally bounded until Phase 7, but every
tool is independently discoverable, invocable, typed, timeout-controlled, and traced.

## Tool catalog

| Tool | Mode | Purpose and safety boundary |
|---|---|---|
| `search_policy_documents` | Read | Hybrid search with evidence sufficiency, conflicts, and citation validation. |
| `get_policy_section` | Read | Exact policy/section lookup returning only authoritative indexed chunks. |
| `lookup_employee_profile` | Read | Minimum synthetic employee facts needed for guidance. |
| `check_pto_balance` | Read/calculation | Weekday and hours calculation against a read-only balance; never approves or changes PTO. |
| `lookup_benefits_status` | Read | Minimum-necessary synthetic eligibility and enrollment fields. |
| `check_policy_compliance` | Deterministic calculation | Bounded international-work, PTO, and home-office-expense rules; never returns an approval. |
| `draft_hr_email` | Draft only | Returns labelled text with `sent=false` and `persisted=false`. |
| `create_mock_hr_ticket` | Confirmation-gated mock action | Creates an in-memory synthetic ticket only with signed confirmation proof; no production system is connected. |

Every tool exposes a generated MCP input schema and structured output schema. Unknown employee or
policy identifiers return explicit not-found results where appropriate; invalid or inconsistent
arguments fail schema validation or return an MCP error without trusted structured content.

## Shared execution controls

`MCPToolExecutor` applies the same controls to discovery and invocation:

- one configured timeout for discovery, transport reads, and each call;
- sequential trace numbers, status, duration, and bounded result summaries;
- removal of authorization, secret, API-key, and confirmation-token fields;
- redaction of ticket summaries and email context from traces; and
- errors and timeouts recorded before the exception reaches the workflow.

The architectural test rejects direct `app.data`, `app.rag`, `peopleops_mcp.tools`, or
`peopleops_mcp.actions` imports from `app/agent`.

## Confirmation-gated mock ticket sequence

1. Prepare a sanitized action preview with category, priority, affected synthetic employee,
   derived routing, summary, and idempotency key.
2. Show the preview to the user. No create-tool call occurs in this state.
3. Record explicit user confirmation and issue a signed, expiring token bound to the exact preview.
4. Invoke `create_mock_hr_ticket` with the unchanged arguments, idempotency key, and token.
5. Validate signature, expiry, recorded confirmation, and the complete action fingerprint.
6. Create one process-local synthetic ticket, or return `already_created` with the same ticket for a
   repeated idempotency key.

Changing priority, summary, employee, routing inputs, category, or idempotency key after confirmation
invalidates the action. Preview IDs and fabricated tokens cannot authorize creation. The signing
secret is environment-based; Render generates it. Local previews and tickets expire on restart by
design, and committed seed files are never modified.

## Deterministic compliance rules

The compliance tool supports exactly three Phase 7 workflow inputs:

- `international_remote_work`: baseline employment/service criteria, 1-20 day short-term and 21-30
  day exceptional categories, expanded approvals, and clarification for country risk;
- `pto_request`: scheduled weekdays, requested hours, available balance, 5/10/20-business-day normal
  notice bands, and manager approval dependency; and
- `home_office_expense`: RFT/RPT plus Hybrid/Remote eligibility, CAD 500 or USD 375 ordinary cap,
  preapproval, and employee-paid remainder.

Results are deterministic screens labelled `conditionally_eligible`, `not_eligible`,
`needs_clarification`, or `not_found`. `decision_is_approval` is always false.

## Developer verification

Run the focused Phase 6 suite:

```powershell
python -m pytest tests/test_phase6_tool_data.py `
  tests/test_phase6_action_safety.py tests/test_phase6_mcp.py
```

Run the complete gate before publishing:

```powershell
.\scripts\check.ps1
```

The focused suite proves all eight discovered schemas and calls, exact-section behavior, PTO and
benefits privacy, three compliance modes, draft-only output, timeout traces, token redaction,
confirmation refusal, tamper and expiry rejection, idempotency, and unchanged seed files.

The committed machine-readable run is
`evaluation/results/phase6_mcp_validation.json`. It passed 8/8 discovery, 8/8 input schemas, 8/8
output schemas, and 8/8 traced calls; rejected the unsigned action; returned `already_created` for
the idempotent repeat; exposed no confirmation token in the trace; and left the ticket seed hash
unchanged. The recorded per-tool durations are warm local observations, not hosted latency claims.

## Phase boundary

Phase 6 completed the tool layer. Phase 7 now selects and sequences these tools in typed workflows,
including clarification, retry, evidence, citation, escalation, and user-confirmation states. Phase
8 will expose those flows through the approved evidence-first interface.
