# Evaluation

The versioned gold suite is `gold_cases.json`. It contains 25 synthetic cases defined before retrieval, MCP, and agent behavior are implemented. The fixed evaluation date is **2026-08-17**.

The suite covers straightforward policy questions, multi-document questions, employee/tool workflows, clarification, escalation, privacy, out-of-scope handling, and confirmation safety. Each case records observable facts, exact policy sections, required and forbidden tools, expected outcome, answer constraints, and safety behavior.

Machine-readable JSON Schemas are committed under `schemas/`. See `docs/data-contracts.md` for the contract reference, validation commands, and case-authoring guide.

Phase 10 will add execution runners, scoring, results, latency measurements, and retrieval ablations. Phase 2 defines what success means; it does not report runtime quality before those capabilities exist.
