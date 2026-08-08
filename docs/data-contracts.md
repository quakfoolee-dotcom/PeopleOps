# Data contracts and evaluation guide

Phase 2 freezes the interfaces and expected behavior that later runtime phases must satisfy. These contracts do not claim that `/chat`, retrieval, or live MCP transport is implemented yet.

## Fixed synthetic date

All deterministic examples and automated evaluations use **2026-09-01**, the corpus effective date. The default is defined in `app/core/constants.py` and can be configured with `SYNTHETIC_AS_OF_DATE`. Evaluation runs must record the suite date and must not silently substitute the wall-clock date.

## Runtime API contracts

`app/api/contracts.py` defines strict Pydantic models with unknown fields rejected:

- `ChatRequest`: request ID, message, optional synthetic employee ID, as-of date, and optional confirmation token.
- `Citation`: stable policy and section identifiers, source title, bounded supporting snippet, policy version, source format, and path.
- `ToolTraceEntry`: ordered tool name, sanitized arguments, status, bounded result summary, duration, and error code where required.
- `PendingActionPreview`: a confirmation-gated preview for synthetic ticket creation.
- `ChatResponse`: final status and outcome, answer, citations, tool trace, and optional pending action.

The response contract enforces that a pending action exists exactly when the workflow is awaiting confirmation. Trace and preview arguments reject nested keys commonly used for credentials. Operational traces contain evidence and tool activity, never hidden chain-of-thought.

Committed JSON Schemas are under `evaluation/schemas`. Regenerate them after an intentional model change:

```powershell
.\.venv\Scripts\python.exe scripts\export_contract_schemas.py
```

Verify that committed schemas match the Pydantic source:

```powershell
.\.venv\Scripts\python.exe scripts\export_contract_schemas.py --check
```

CI performs the drift check.

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

## Adding or changing a case

1. Confirm the prompt represents a distinct requirement or failure mode.
2. Use policy and section IDs that exist in the corpus.
3. Declare tool expectations before runtime implementation.
4. State observable facts and safety behavior, not preferred writing style alone.
5. Preserve the required category distribution or document and approve a suite-version change.
6. Run schema export verification and the complete test suite.

Changing a gold expectation after observing a poor runtime result is allowed only to correct an identified specification error; it must not be used to hide a product failure.
