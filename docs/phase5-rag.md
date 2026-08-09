# Phase 5 hybrid RAG

Phase 5 replaces the Phase 4 hard-coded policy matcher with deterministic, persisted hybrid
retrieval while preserving the rule that the orchestrator may obtain policy evidence only through
MCP.

## Implemented pipeline

1. Read `policy_corpus/corpus_docs/policy_manifest.json` and accept only the declared
   `runtime_corpus` sources.
2. Parse ten Markdown policies by stable `## SECTION-ID. Heading` boundaries.
3. Parse two authoritative PDF policies with `pypdf`, remove contents/header/footer noise, and
   preserve the physical source page for each section.
4. Split oversized sections by paragraph with a 240-word target and 40-word overlap. The current
   corpus produces 169 stable chunks for 169 sections.
5. Enrich every chunk with policy ID/title, section ID/title, version, effective date, owner,
   applicability, source format/path, page, and a stable chunk ID.
6. Generate a 384-dimensional deterministic local feature-hashing embedding over normalized word
   and bigram features. The model has no network, API-key, or paid-service dependency.
7. Combine BM25-style keyword scores and embedding cosine scores at weights 0.62/0.38.
8. Decompose multi-policy PeopleOps questions into bounded topic facets and preserve representative
   evidence for each required policy and facet.
9. Deduplicate results by policy section, enforce evidence coverage, detect duplicate-version or
   inconsistent-authoritative-text conflicts, and reject out-of-domain prompts.
10. Validate every returned citation against the exact indexed chunk before it crosses the MCP
    boundary.

The local embedding is intentionally lightweight for deterministic CI and Render's free service.
It is not presented as a neural embedding model. `HybridIndex` and `HybridRetriever` isolate that
choice so a future local neural provider can replace it without changing MCP or API contracts.

## Persisted index

The committed index is `policy_corpus/index/phase5_index.json`. It contains a SHA-256 corpus
fingerprint, index/model versions, chunk configuration, enriched chunks, and their embeddings. The
application loads it when current and rebuilds it atomically when source/configuration drift is
detected.

Build or verify it with:

```powershell
python scripts/build_rag_index.py
python scripts/build_rag_index.py --check
```

CI and the production Docker build perform the drift check. A policy change is incomplete until the
persisted index is rebuilt and committed.

## Retrieval evaluation

`scripts/evaluate_rag.py` evaluates every gold case that declares policy evidence: 24 cases and 48
expected policy sections. The Phase 5 warm local ablation selected hybrid retrieval at `k=8`:

| Configuration | Gold evidence recall | Warm p50 | Warm p95 |
|---|---:|---:|---:|
| Dense-only, k=5 | 83.33% | 28.32 ms | 36.62 ms |
| Hybrid, k=5 | 95.83% | 30.85 ms | 43.38 ms |
| Hybrid, k=8 | 100.00% | 27.95 ms | 37.00 ms |

The latency values are one deterministic Windows development run, not hosted-service latency. Raw
case results and the CSV summary are committed under `evaluation/results`. Phase 10 repeats the
measurement across cold and warm deployed runs.

Regenerate the artifacts with:

```powershell
python scripts/evaluate_rag.py --write
```

The command fails if the selected hybrid `k=8` configuration falls below 95% evidence recall.

## Safety behavior

- A remote international-work answer requires evidence from international-work, remote-work, and
  security policies.
- A metadata filter that removes a required policy makes evidence insufficient.
- Out-of-domain questions return no evidence.
- Conflicting retrieved versions or inconsistent authoritative text block sufficiency.
- Citation IDs, metadata, source paths, and text must match a retrieved indexed chunk exactly.
- Retrieved text remains evidence data; it is never executed as instructions.

Evidence sufficiency means the retriever has enough policy material to support the next workflow
decision. An ambiguous request can have sufficient evidence for asking a clarification while still
being insufficient for a final approval or eligibility decision.

## Phase boundary

At the Phase 5 boundary, `/chat` remained intentionally bounded to the E-1007 Germany workflow.
Phase 6 added the complete eight-tool MCP suite; Phase 7 now consumes this retriever in the typed
workflows; Phase 8 implements the approved evidence-first `/chat` workspace.
