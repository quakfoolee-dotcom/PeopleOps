# AI tooling disclosure

## Tools used

OpenAI Codex was used during Phases 1 through 6 to:

- review the assignment requirements and Score 5 delivery plan;
- inspect the GitHub repository and local policy-corpus package;
- propose the implementation order and architecture boundaries;
- scaffold the FastAPI and React/Vite foundation;
- draft automated tests, CI configuration, and project documentation;
- check product naming consistency and validate policy PDF artifacts;
- run local validation and prepare the Git commit.
- translate the approved ten-phase plan into GitHub milestones and acceptance issues;
- draft and validate strict API, citation, operational-trace, pending-action, and evaluation contracts;
- create the initial 25-case gold evaluation suite from the reviewed synthetic policy corpus.
- define strict synthetic employee, manager, location, PTO, benefits, ticket, and manifest contracts;
- generate deterministic fixtures, integrity checks, JSON Schemas, and a reproducible SQLite materialization path;
- identify and correct the mismatch between the original evaluation snapshot date and the policy corpus effective date.
- implement and test the official MCP Streamable HTTP server, client discovery, and two read-only tools;
- implement the bounded `/chat` workflow, fail-closed behavior, citations, and sanitized trace;
- build and visually verify the interactive Phase 4 demonstration interface;
- prepare the Render Blueprint, operating guide, and deployment smoke-test procedure;
- guide the owner-controlled Render authorization and verify the hosted UI, health, and chat flow.
- compare the proposed evidence-first UI wireframe with the working Phase 4 interface and record the
  corrected Phase 8 design decision;
- implement and test authoritative Markdown/PDF ingestion, deterministic local embeddings,
  BM25-style scoring, hybrid ranking, query decomposition, evidence gates, and citation validation;
- build the persisted index and retrieval-ablation workflow, analyze initial recall errors, and
  improve broad gold-suite evidence recall without changing the pre-implementation gold cases.
- implement and test the remaining exact-section, PTO, benefits, compliance, draft-email, and
  confirmation-gated mock-ticket MCP tools;
- create a shared timeout-controlled executor with sanitized traces and verify that the agent cannot
  import data, RAG, tool, or action implementations directly;
- design and test signed expiring confirmation proof, exact preview binding, idempotency, trace
  redaction, and process-local-only mock mutation behavior.

## Human responsibility and review

The project owner remains responsible for correctness, security, academic integrity, and final submission. AI-generated work is reviewed through source inspection, automated tests, deterministic corpus checks, build verification, and documented acceptance criteria.

## What worked well

AI assistance was effective for mapping rubric requirements to repository evidence, creating consistent project structure, identifying integration risks early, and producing repeatable validation commands.

## Limitations

Generated code and documentation are not accepted as correct merely because they compile. MCP and
RAG behavior are checked through automated integration, retrieval, citation, index-drift, and live
HTTP tests. The Phase 5 local feature-hashing embedding is deliberately small and deterministic; it
has less open-domain semantic capacity than a neural model and is paired with bounded PeopleOps
query decomposition. The Phase 6 confirmation service and mock tickets are intentionally
single-process demonstration state, not durable workflow infrastructure. Wider agent workflow
safety, provider integration, hosted reliability, and final evaluation still require
implementation-specific tests and human review in later milestones.

This document will be updated throughout the project.
