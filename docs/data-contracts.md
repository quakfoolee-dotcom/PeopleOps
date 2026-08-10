# Data contracts and evaluation guide

Phase 2 froze the interfaces and expected behavior. Phases 3 through 6 now implement the structured
data, retrieval, bounded `/chat` path, live MCP transport, and complete tool suite against those
predefined expectations.

## Demo policy as-of date

All deterministic examples and automated evaluations use **2026-09-01**, the corpus effective date.
The UI labels this the demo policy as-of date so it is not mistaken for today's date. The default is
defined in `app/core/constants.py` and can be configured with `SYNTHETIC_AS_OF_DATE`. Evaluation
runs must record the suite date and must not silently substitute the wall-clock date.

## Runtime API contracts

`app/api/contracts.py` defines strict Pydantic models with unknown fields rejected:

- `AttachmentUploadRequest`: bounded filename, allowed media type, and base64 content for
  non-persistent extraction.
- `AttachmentContext`: extracted filename, media type, bounded text, original byte size, and
  truncation flag.
- `ChatRequest`: request ID, message, optional synthetic employee ID, optional use-case hint,
  optional extracted attachment context, as-of date, and optional confirmation token.
- `Citation`: stable policy, section, and chunk identifiers; source title; bounded supporting
  snippet; policy version and effective date; source format/path; optional PDF page; and retrieval
  score.
- `ToolTraceEntry`: ordered tool name, sanitized arguments, status, bounded result summary, duration, and error code where required.
- `DecisionSummary`: UI-ready status, duration or request amount, policy category, required approvals,
  clarification needs, and ordered next steps produced from the same typed workflow evidence as the
  answer.
- `PendingActionPreview`: a confirmation-gated preview with confirmation ID and expiry for synthetic
  ticket creation.
- `EmailDraft`: a UI-ready, explicitly unsent and non-persistent artifact with recipient, subject,
  body, stable draft ID, draft type, and safety warnings.
- `ChatResponse`: selected remote-work, PTO, expense, mock-ticket, policy-guidance, or unsupported
  workflow; terminal workflow state; final status and outcome; answer;
  optional decision summary, citations, tool trace, email draft, and pending action.
- `ConfirmMockTicketRequest` and `ConfirmMockTicketResponse`: explicit-true confirmation and the
  signed proof returned to the unchanged follow-up request.

The response contract enforces that a pending action exists exactly when the workflow is awaiting
confirmation and that an email draft exists exactly when the outcome is `draft_only`. Draft
artifacts must remain `sent=false` and `persisted=false`. Trace and preview arguments reject nested
keys commonly used for credentials. Operational traces contain evidence and tool activity, never
hidden chain-of-thought.

Committed JSON Schemas are under `evaluation/schemas`. Regenerate them after an intentional model change:

```powershell
.\.venv\Scripts\python.exe scripts\export_contract_schemas.py
```

Verify that committed schemas match the Pydantic source:

```powershell
.\.venv\Scripts\python.exe scripts\export_contract_schemas.py --check
```

CI performs the drift check.

## MCP tool contracts

`peopleops_mcp/schemas.py` defines strict structured results for policy search, exact-section
retrieval, employee profile, PTO balance and calculation, benefits status, compliance, email draft,
ticket preview, and mock-ticket action. MCP discovery exposes both input and output JSON Schemas for
all eight tools.

Read tools return `found=false` rather than inventing missing records. Compliance results include
the applicable policy-section references, calculations, conditions, clarification fields, and
`decision_is_approval=false`. Policy-only hypothetical remote-work and expense checks may omit an
employee ID; employee-specific and PTO checks require one. Drafts require `sent=false` and
`persisted=false`.

The action contract separates a pre-tool preview from the post-confirmation create call. A signed
token binds confirmation ID, expiry, and the exact preview fingerprint. The create result declares
that it is synthetic and process-local. Confirmation tokens and sensitive free text are excluded or
redacted from `ToolTraceEntry.sanitized_arguments`.

## Synthetic operational-data contracts

Phase 3 adds strict contracts for locations, employees, manager relationships, PTO balances and transactions, benefits, historical mock tickets, and the seed manifest. Their committed JSON Schemas are under `mock_data/schemas`.

The manifest requires `synthetic_only=true`, the fixed snapshot date, expected files, record counts, and SHA-256 checksums. Semantic validation then enforces employee and location references, an acyclic manager hierarchy, one balance and benefits record per employee, no future-dated records, and the stable employee IDs required by the gold suite.

Run `python scripts/validate_phase3_assets.py` to validate both the policy corpus and structured snapshot and to prove the data can be loaded into a foreign-key-clean SQLite database.

## Gold evaluation suite

`evaluation/gold_cases.json` is the authoritative pre-implementation expectation set. Its 25 cases use this fixed distribution:

| Category | Cases |
|---|---:|
| Straightforward policy | 7 |
| Multi-document policy | 5 |
| Employee/tool workflow | 6 |
| Ambiguous/clarification | 4 |
| Out-of-scope/safety | 3 |

Every case declares:

- a stable case ID, title, category, and prompt;
- the expected facts and exact policy/section targets;
- required, forbidden, and post-confirmation tools;
- the expected workflow outcome;
- answer constraints and safety behavior;
- optional synthetic employee context and tags.

Post-confirmation tools are intentionally separate from required tools. `create_mock_hr_ticket` cannot appear as a pre-confirmation requirement.

## Validation

Run the focused checks:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_api_contracts.py tests/test_evaluation_suite.py
```

Semantic validation additionally checks:

- exactly 25 unique case IDs and the required category counts;
- the fixed as-of date;
- every referenced policy section against master Markdown headings;
- every tool name against the eight declared MCP contracts;
- at least two policies for multi-document cases;
- an employee ID for employee/tool workflows;
- the confirmation boundary for synthetic ticket creation.

Phase 10 then executes all 25 versioned cases against the real orchestrator and MCP boundary. Its
committed JSON/CSV report records every response, citation, trace, outcome, metric, latency sample,
reliability run, safety check, and error-analysis item.

## Adding or changing a case

1. Confirm the prompt represents a distinct requirement or failure mode.
2. Use policy and section IDs that exist in the corpus.
3. Declare tool expectations before runtime implementation.
4. State observable facts and safety behavior, not preferred writing style alone.
5. Preserve the required category distribution or document and approve a suite-version change.
6. Run schema export verification and the complete test suite.

Changing a gold expectation after observing a poor runtime result is allowed only to correct an identified specification error; it must not be used to hide a product failure.
