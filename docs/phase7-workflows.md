# Phase 7 bounded workflows and safety

Phase 7 connects the complete MCP tool suite to deterministic typed workflows for international
remote work, PTO guidance, home-office expense compliance, and confirmation-gated mock HR tickets.
The orchestrator does not use an unrestricted agent loop and does not access policy or employee
stores directly.

## Workflow catalog

| Workflow | Required inputs | MCP sequence | Successful outcome |
|---|---|---|---|
| International remote work | Employee ID, destination, and duration or exact dates | Profile, hybrid search, four exact sections, compliance | Conditional or not eligible, with exact citations and required approvals |
| PTO guidance | Employee ID and exact start/end dates | Profile, balance, hybrid search, two exact sections, compliance, optional draft | Conditional guidance or `draft_only`; no balance mutation, sent email, or persisted draft |
| Home-office expense | Employee ID, amount, and CAD/USD currency | Profile, hybrid search, three exact sections, compliance | Conditional or not eligible, with cap, remainder, and approval path |
| Mock HR ticket | Employee ID, concern, unchanged request ID, and explicit confirmation proof | Profile, hybrid search, three exact sections, preview, confirmed create | One process-local synthetic ticket, idempotent on repeat |

Every completed answer contains only citations returned by exact `get_policy_section` calls. Hybrid
search must first pass its sufficiency and conflict checks. The response exposes the selected
`workflow` and terminal `workflow_state` in addition to the request ID, outcome, citations, and
sanitized operational trace.

## Bounded state machine

The allowed states are `classify`, `clarify`, `discover`, `profile`, `retrieve`, `evidence`,
`compliance`, `draft`, `confirmation`, `action`, `escalate`, and `respond`. A transition allow-list
rejects invalid jumps. Each workflow has a maximum of ten logical tool calls; normal primary flows
use no more than eight operations and the optional remote-work draft uses nine. Discovery or a tool
call receives at most two total attempts. Every failed and successful attempt remains visible in
the operational trace.

Classification and input validation happen before MCP access. A missing or conflicting employee
ID, relative PTO date, missing destination/duration, or incomplete expense amount/currency returns
`needs_clarification` with no tool trace or citations.

## Safety gates

- **Tool availability:** only tools required by the selected workflow are mandatory. A missing or
  unavailable required tool returns a fail-closed service error after the bounded retry.
- **Structured facts:** an unknown employee or missing PTO record never becomes an inferred fact.
- **Evidence sufficiency:** failed hybrid coverage stops before exact-section or compliance work.
- **Policy conflicts:** any search or exact-section conflict escalates without citations or a policy
  conclusion.
- **Citation gate:** each material workflow requires its declared exact policy/section pairs.
- **Approval boundary:** compliance results are guidance; they never approve remote work, PTO, or an
  expense.
- **Draft boundary:** remote-work and PTO drafts are returned as a structured `email_draft` artifact
  with recipient, subject, body, `sent=false`, and `persisted=false`. Both the MCP result and API
  response enforce the unsent, non-persistent state.
- **Confirmation boundary:** a ticket create call cannot occur before explicit confirmation. Tokens
  are signed, expiring, bound to the exact preview, and removed from traces.

## Manual use cases

Start the API, then send any of these bodies to `POST /chat`:

```json
{"employee_id":"E-1007","message":"Can I work remotely from Germany for six weeks?"}
```

```json
{"employee_id":"E-1021","message":"Can I take PTO from September 21 through September 23, 2026? Check my balance and draft a message to my manager."}
```

```json
{"employee_id":"E-1014","message":"Can employee E-1014 be reimbursed for a CAD 900 home-office chair?"}
```

For a mock ticket, preserve the first response's `request_id` and action arguments:

1. `POST /chat` with employee E-1011 and a request to prepare an HR ticket.
2. Verify `status=awaiting_confirmation`, inspect `pending_action`, and confirm that the trace has no
   `create_mock_hr_ticket` call.
3. `POST /actions/mock-tickets/confirm` with the preview `confirmation_id` and
   `user_confirmed=true`.
4. Re-submit the same `/chat` request with the same `request_id` and returned
   `confirmation_token`.
5. A repeat returns the same ticket as `already created`; committed fixtures remain unchanged.

Phase 8 will add the product confirmation card. Phase 7 deliberately exposes the complete sequence
through the typed API first.

## Verification

Run the focused suite and machine-readable evaluation:

```powershell
python -m pytest tests/test_phase7_workflows.py tests/test_phase7_safety.py `
  tests/test_phase7_evaluation.py
python scripts/evaluate_workflows.py
```

The committed result is `evaluation/results/phase7_workflows.json`. It records three repeat runs for
each primary workflow, the expense backup, input clarification, unavailable-service and conflict
behavior, preview-before-create enforcement, idempotency, trace redaction, and seed immutability.

## Phase boundary

Phase 7 completes workflow selection and safety sequencing. Phase 8 will implement the approved
evidence-first workspace with preset tasks, citation and trace inspection, request/service status,
and the interactive confirmation card.
