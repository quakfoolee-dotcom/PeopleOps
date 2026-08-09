# Risk register and known limitations

This register covers the deployed synthetic demonstration and the evidence used for final
submission. It is not a production HR-system authorization assessment.

| Risk | Implemented control | Residual risk and owner | Verification evidence |
|---|---|---|---|
| A generated answer adds unsupported policy facts | The LLM can only summarize a completed typed workflow; protected facts, numbers, identifiers, and exact citations are validated before display. Invalid output falls back to the verified deterministic result. | A novel paraphrase can still be misleading. Product owner reviews cited source text before relying on guidance. | Provider contract tests, `/chat` generation metadata, Phase 10 groundedness and citation metrics |
| Policy or synthetic data is mistaken for current company or legal guidance | Every record is fictional, the UI shows the synthetic demo banner and fixed policy as-of date, and responses distinguish guidance from approval. | A screenshot can lose surrounding labels. Presenter must state the synthetic scope during the demo. | UI tests, demo script, `SYNTHETIC_AS_OF_DATE`, corpus manifest |
| Policy versions drift from the RAG index | Corpus and index manifests are checksum-validated; CI fails on index or schema drift. | An intentional policy update requires explicit re-ingestion and gold-case review. Maintainer owns the update. | Phase 3 validation, Phase 5 index check, CI backend gate |
| Retrieval omits required evidence | Hybrid retrieval uses query decomposition, exact-section retrieval, evidence sufficiency, conflict, and citation gates. | The deterministic feature-hashing embedding is weaker on open-domain language. Unsupported wording may clarify or escalate. | Phase 5 ablation, Phase 10 retrieval recall, error analysis |
| MCP is bypassed or unavailable | The orchestrator uses the official MCP client, discovers typed tools, applies timeouts and one bounded retry, and cannot import tool/data/RAG implementations directly. | A service outage prevents the workflow; it fails closed rather than guessing. | Architecture tests, eight-tool discovery test, sanitized operational traces |
| A write-like action occurs without consent | The ticket path requires a preview, signed expiring proof bound to the exact request, explicit confirmation, redacted trace, and idempotency key. | Tickets are process-local demo records and are lost on restart. They are not production workflow records. | Phase 6/7 safety tests and Phase 10 action-safety metric |
| Sensitive data or secrets leak through responses or traces | Only synthetic records are committed; traces use allow-listed summaries and redact confirmation tokens; secrets remain environment variables. | Provider requests still transmit the bounded verified prompt to the configured service. Deployment owner controls provider terms and key. | Secret scanning in review, trace tests, Render masked environment variables |
| Deterministic intent routing misses valid wording | Workflows are bounded and typed; unrecognized requests return a controlled answer instead of invoking arbitrary tools. | This is not a general HR chatbot. Maintainer expands routes only with new gold cases and tests. | Phase 10 25-case report and the documented `EVAL-SAFE-003` miss |
| Free-tier hosting causes slow or unavailable first requests | Health checks and smoke automation allow a bounded cold-start window and record wake time separately from endpoint latency. | Render may spin down after inactivity and OpenRouter may impose quota/model-routing delays. Presenter warms the app during preflight. | Hosted-smoke artifacts, `deployed.md`, demo rehearsal preflight |
| Evaluation overfits the fixed suite | Gold expectations were defined before implementation, include ambiguous and safety cases, and remain versioned. Error analysis is retained rather than editing away a miss. | Twenty-five synthetic cases cannot represent every PeopleOps scenario. Product owner treats metrics as bounded evidence. | Git history, gold-suite schema, Phase 10 raw case results |

## Explicit non-goals

- no real employee, payroll, benefits, leave, or case-management integration;
- no autonomous approval, legal interpretation, medical advice, or live web search;
- no durable database mutation or production authentication/authorization model;
- no hidden chain-of-thought exposure; the interface provides observable evidence and tool traces;
- no claim that local or hosted latency measurements are a service-level guarantee.
