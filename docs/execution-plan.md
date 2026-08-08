# Authoritative execution plan

This ten-phase plan controls implementation order. A phase is complete only when its exit criterion is implemented, tested, documented, committed to `main`, and verified by CI. Work completed early for a later phase is recorded as a partial foundation and does not change the sequence.

| Phase | Work | Exit criterion | Reasoning | Status |
|---|---|---|---|---|
| 1. Foundation | Repository structure, dependencies, configuration, Docker, traceability, and GitHub planning | `/health` runs locally; backend imports and frontend builds in CI; all phases have GitHub milestones and acceptance issues | Establish reproducibility and map requirements to code, tests, documentation, and demo evidence. | Ready |
| 2. Evaluation and data contracts | Twenty-five gold cases, API/citation/trace schemas, and fixed synthetic date | Every case declares facts, policy sections, tools, outcome, and safety behavior and passes schema/semantic validation | Define success before implementation to prevent subjective evaluation and missing scenarios. | Ready |
| 3. Policy corpus and mock data | Coherent policies plus employee, PTO, benefits, manager, location, and ticket data | Corpus and synthetic-data validation pass | Retrieval and workflows depend on consistent evidence and deterministic structured data. | In progress: corpus ready; structured data next |
| 4. Thin vertical slice | API to orchestrator to discovered MCP tools to cited response and trace; deploy immediately | MCP discovery/invocation test and hosted `/health` pass | Validate the highest-risk architectural boundary before implementing the full tool suite. | Planned |
| 5. RAG implementation | Format-aware ingestion, hybrid retrieval, evidence and citation validation | Known and multi-document queries retrieve correct evidence; fabricated citations fail | Hybrid retrieval covers semantic language and exact policy terminology. | Planned |
| 6. MCP tool suite | Implement all eight planned tools through MCP | All tools are discoverable, schema-valid, traced, timeout-controlled, and tested | Enforce genuine MCP integration rather than direct data or retrieval access. | Planned |
| 7. Agent workflows and safety | Bounded remote-work, PTO, and expense workflows with safety gates | Primary workflows and failure/safety cases pass repeatedly | Typed bounded workflows provide testable and safer behavior. | Planned |
| 8. Product interface | Chat, demo tasks, citations, traces, status, and confirmation experience | Grader can reproduce both workflows and inspect evidence | Expose operational evidence without exposing hidden chain-of-thought. | Foundation shell ready; functionality planned |
| 9. CI/CD and deployment | Complete checks, deterministic CI substitutes, and gated hosting | Hosted application and health smoke tests pass after required checks | Deploy from the vertical slice onward and gate releases on verification. | CI/Docker baseline ready; hosting planned |
| 10. Evaluation and submission | Gold-suite run, ablations, metrics, documents, access, and demo | Every Score-5 gate passes | Evaluation and demo evidence are graded deliverables. | Planned |

## GitHub planning map

| Phase | Milestone | Acceptance issue |
|---|---|---|
| 1 | [Foundation](https://github.com/quakfoolee-dotcom/PeopleOps/milestone/1) | [#2](https://github.com/quakfoolee-dotcom/PeopleOps/issues/2) |
| 2 | [Evaluation and data contracts](https://github.com/quakfoolee-dotcom/PeopleOps/milestone/2) | [#1](https://github.com/quakfoolee-dotcom/PeopleOps/issues/1) |
| 3 | [Policy corpus and mock data](https://github.com/quakfoolee-dotcom/PeopleOps/milestone/3) | [#3](https://github.com/quakfoolee-dotcom/PeopleOps/issues/3) |
| 4 | [Thin vertical slice](https://github.com/quakfoolee-dotcom/PeopleOps/milestone/4) | [#5](https://github.com/quakfoolee-dotcom/PeopleOps/issues/5) |
| 5 | [RAG implementation](https://github.com/quakfoolee-dotcom/PeopleOps/milestone/5) | [#4](https://github.com/quakfoolee-dotcom/PeopleOps/issues/4) |
| 6 | [MCP tool suite](https://github.com/quakfoolee-dotcom/PeopleOps/milestone/6) | [#6](https://github.com/quakfoolee-dotcom/PeopleOps/issues/6) |
| 7 | [Agent workflows and safety](https://github.com/quakfoolee-dotcom/PeopleOps/milestone/7) | [#7](https://github.com/quakfoolee-dotcom/PeopleOps/issues/7) |
| 8 | [Product interface](https://github.com/quakfoolee-dotcom/PeopleOps/milestone/8) | [#8](https://github.com/quakfoolee-dotcom/PeopleOps/issues/8) |
| 9 | [CI/CD and deployment](https://github.com/quakfoolee-dotcom/PeopleOps/milestone/9) | [#9](https://github.com/quakfoolee-dotcom/PeopleOps/issues/9) |
| 10 | [Evaluation and submission](https://github.com/quakfoolee-dotcom/PeopleOps/milestone/10) | [#10](https://github.com/quakfoolee-dotcom/PeopleOps/issues/10) |

## Next action

Phase 3 will add deterministic synthetic employee, manager, location, PTO, benefits, and ticket fixtures. The records must satisfy the facts assumed by the gold employee-workflow cases and pass referential-integrity and synthetic-only validation before the Phase 4 vertical slice begins.
