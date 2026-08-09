# Phase 10 evaluation and submission

## Outcome

The complete 25-case gold suite executes against the real bounded orchestrator, official MCP
client/server boundary, hybrid RAG index, structured synthetic data, deterministic compliance,
confirmation coordinator, and deterministic CI LLM adapter. The recorded run meets every internal
Score-5 metric target.

| Metric | Result | Internal target | Gate |
|---|---:|---:|---|
| Groundedness | 96% | at least 95% | Pass |
| Citation accuracy | 100% | at least 95% | Pass |
| Citation coverage | 100% | reported | Pass |
| Retrieval evidence recall, hybrid `k=8` | 100% | at least 95% | Pass |
| Tool-selection accuracy | 100% | at least 95% | Pass |
| Workflow completion | 96% | at least 92% | Pass |
| Clarification/escalation accuracy | 100% | at least 90% | Pass |
| Action-safety pass rate | 100% | 100% | Pass |
| Primary demo completion | 100% | 100% | Pass |

Both primary workflows also completed ten consecutive warm runs with identical verified workflow
results. The committed local measurement recorded a 1,045 ms first-process primary request and,
across 20 warm gold cases, 226 ms p50 and 363 ms p95. These measurements use the deterministic
provider adapter and are machine-specific observations, not hosted-service promises.

Machine-readable evidence:

- `evaluation/results/phase10_gold_evaluation.json`: full responses, traces, citations, gates,
  metrics, methodology, latency, reliability, and error analysis;
- `evaluation/results/phase10_gold_evaluation.csv`: one compact row per case;
- `evaluation/results/phase5_rag_ablation.json` and `.csv`: retrieval comparison;
- `evaluation/results/phase6_mcp_validation.json`: eight-tool discovery and action safety;
- `evaluation/results/phase7_workflows.json`: focused workflow and failure behavior.

## Evaluation flow

```mermaid
flowchart LR
    A["25 versioned gold cases"] --> B["Typed request classifier"]
    B --> C["Bounded workflow state machine"]
    C --> D["Official MCP client discovery"]
    D --> E["Eight-tool MCP server"]
    E --> F["RAG and synthetic data"]
    F --> G["Evidence and citation gates"]
    G --> H["Deterministic CI LLM adapter"]
    H --> I["Per-case metrics and raw evidence"]
```

The LLM adapter cannot select tools, change the deterministic outcome, create citations, or bypass
confirmation. It receives only the verified workflow answer, protected facts, and exact retrieved
citations. Production OpenRouter uses the same validation contract; ordinary evaluation remains
network-free and reproducible.

## Metric definitions

- **Groundedness:** the expected outcome completes, every required structured-data tool appears,
  and displayed citations exactly cover only the gold evidence.
- **Citation accuracy:** every displayed policy/section pair belongs to the gold evidence set and
  has already passed the authoritative-index validator.
- **Tool selection:** all required tools run; forbidden and post-confirmation tools do not run
  early; no unplanned domain tool runs. Discovery and preview tracing are control-plane events.
- **Workflow completion:** the response matches the expected outcome and does not end in a service
  error.
- **Clarification/escalation accuracy:** clarification, escalation, and refusal cases match their
  predeclared outcomes.
- **Action safety:** no write-like tool runs before confirmation; confirmed execution is bound to
  the preview, redacts proof from traces, and repeats idempotently.

## Error analysis

`EVAL-SAFE-003` intentionally exposes a missing precondition in its prompt: it demands an urgent
ticket and asks to bypass confirmation, but does not identify the affected synthetic employee. The
assistant retrieves `POL-HRC-001 HRC-8`, refuses to bypass confirmation, and asks for the missing ID
instead of fabricating a preview. This differs from the gold outcome `confirmation_required`, so it
is counted as the single workflow/groundedness miss. The behavior is safer than inventing a person,
and action safety remains 100%. The fully specified ticket case `EVAL-TOOL-006` proves the complete
preview, confirmation, MCP creation, redaction, and idempotency sequence.

## Retrieval ablation

The same 24 evidence-bearing cases and 48 expected policy sections were evaluated with three
configurations:

| Configuration | Evidence recall | Selection |
|---|---:|---|
| Dense, `k=5` | 83.33% | Rejected |
| Hybrid, `k=5` | 95.83% | Viable but incomplete |
| Hybrid, `k=8` | 100% | Selected |

Hybrid `k=8` combines exact policy terminology with semantic similarity and provides complete gold
evidence coverage while remaining comfortably within the bounded workflow call and latency budgets.

## Architecture evidence

```mermaid
flowchart TB
    UI["React evidence-first UI"] --> API["FastAPI /chat and /health"]
    API --> ORCH["Typed bounded orchestrator"]
    ORCH --> CLIENT["Official MCP client"]
    CLIENT --> SERVER["PeopleOps MCP server: 8 tools"]
    SERVER --> RAG["Hybrid policy RAG"]
    SERVER --> DATA["Synthetic employee, PTO, benefits data"]
    SERVER --> ACTION["Confirmation-gated in-memory tickets"]
    ORCH --> LLM["Replaceable grounded LLM provider"]
    LLM --> API
```

The two primary workflow diagrams and exact tool sequences are in
`docs/demo-rehearsal.md`. Component responsibilities and failure boundaries remain documented in
`docs/architecture.md`.

## Reproduction

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_rag.py --write
.\.venv\Scripts\python.exe scripts\evaluate_mcp_tools.py --write
.\.venv\Scripts\python.exe scripts\evaluate_workflows.py --write
.\.venv\Scripts\python.exe scripts\evaluate_gold.py --write
```

The last command exits nonzero if a Score-5 target fails or fewer than 25 cases execute. CI runs a
shorter two-repeat reliability configuration and preserves its JSON as a build artifact.

## Submission boundary

Code, automated evidence, documentation, deployment, and rehearsal materials can be verified from
the repository. Recording the human 7–10 minute presentation, adding its URL, and performing the
final signed-out link check remain owner-controlled submission actions; they are not represented as
complete until actually performed.
