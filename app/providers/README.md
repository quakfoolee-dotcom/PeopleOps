# Provider adapters

The provider layer is replaceable and has no direct access to the policy index, mock database, MCP
tools, or confirmation service. `PeopleOpsOrchestrator` gives it only the completed deterministic
answer, structured decision, synthetic user prompt, and exact validated citations.

Supported modes:

| `LLM_PROVIDER` | Purpose |
|---|---|
| `not-configured` | Default local mode; returns the verified typed-workflow answer unchanged. |
| `deterministic` | Network-free CI adapter that exercises the synthesis boundary. |
| `openrouter` | OpenAI-compatible `/chat/completions` adapter for the hosted demonstration. |
| `openai-compatible` | Same adapter with a replaceable `LLM_BASE_URL`. |

External output is accepted only when it is valid JSON, cites the complete verified citation set,
uses every required citation marker, preserves protected decision and safety facts, and introduces no
unknown number, employee ID, policy ID, or section ID. A timeout, authentication error, rate limit,
invalid envelope, malformed JSON, missing evidence, or failed grounding check returns the original
verified workflow answer with `generation.mode=deterministic_fallback`.

API keys are read through `LLM_API_KEY` or `OPENROUTER_API_KEY` as a Pydantic `SecretStr`. They are
used only in the authorization header and never appear in health details, chat metadata, traces, or
errors.
