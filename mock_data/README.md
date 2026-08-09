# Deterministic mock data

This directory contains the synthetic operational snapshot used by PeopleOps Assistant. It contains no real employee or company data.

## Snapshot contract

- Organization: fictional Northstar Technologies Inc.
- Fixed as-of date: `2026-09-01`
- Employees: 30
- Locations: 6 across Canada and the United States
- Manager relationships: 29, forming one acyclic hierarchy
- PTO balances: one per employee, plus 15 illustrative transactions
- Benefits: one eligibility/enrollment record per employee
- Tickets: 6 historical, explicitly confirmed mock records

`seed/manifest.json` is authoritative. It declares the schema version, record counts, filenames, SHA-256 checksums, fixed date, and synthetic-only flag. Each JSON dataset is validated by the strict Pydantic contracts in `app/data/contracts.py`; unknown fields are rejected.

The stable employees used by the gold evaluation workflows include `E-1003`, `E-1007`, `E-1011`, `E-1014`, `E-1021`, and `E-1024`. Names and attributes are fictional.

## Validate the corpus and data

From the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\validate_phase3_assets.py
```

This verifies policy count and length, both runtime formats, stable section metadata, policy effective dates, seed checksums, strict schemas, referential integrity, dates, manager hierarchy, gold-case employee coverage, and a temporary SQLite build with foreign-key checks.

## Build a local SQLite database

The JSON files are the committed source of truth. To create a disposable database for inspection or later tool development:

```powershell
.\.venv\Scripts\python.exe scripts\validate_phase3_assets.py `
  --database mock_data/generated/peopleops.db
```

`mock_data/generated/` and database files are ignored by Git. Re-running the command deterministically replaces the requested database only after a complete validated build.

Example read-only inspection:

```powershell
.\.venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('mock_data/generated/peopleops.db'); print(c.execute('select employee_id, role from employees order by employee_id limit 5').fetchall()); c.close()"
```

## Change procedure

1. Update the relevant seed JSON without changing stable IDs used by evaluations.
2. Recalculate the changed file's SHA-256 and update `seed/manifest.json`.
3. Keep every snapshot date aligned with `SYNTHETIC_AS_OF_DATE`.
4. Regenerate schemas with `python scripts/export_contract_schemas.py` after contract changes.
5. Run `python scripts/validate_phase3_assets.py` and the complete `scripts/check.ps1` gate.

Never add actual employee records, personal contact details, secrets, medical details, investigation findings, or production ticket content.

## Phase 6 mock actions

`create_mock_hr_ticket` never writes this directory or a production service. After explicit signed
confirmation it creates a process-local synthetic record with IDs starting at `TKT-9001`. Repeated
use of the same idempotency key returns the original record. Restarting the service clears previews,
tokens, and created mock tickets; the six committed historical fixtures remain authoritative.
