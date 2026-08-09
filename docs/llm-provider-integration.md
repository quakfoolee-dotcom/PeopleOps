# LLM provider integration

## Outcome

PeopleOps Assistant has a provider-independent response-synthesis boundary. The typed state machine,
MCP calls, deterministic compliance result, evidence gate, citations, confirmation gate, and action
decision remain authoritative. A configured model may write a concise plain-language summary only
after those controls complete.

The hosted adapter uses OpenRouter's OpenAI-compatible chat-completions contract. The documented
zero-cost default model is `openrouter/free`; `LLM_MODEL` can pin another model without changing RAG,
MCP, or the workflows. The adapter records the configured and resolved model in sanitized response
metadata.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `not-configured` | `openrouter`, `openai-compatible`, `deterministic`, or disabled. |
| `LLM_MODEL` | `openrouter/free` in `.env.example` | Provider model or router identifier. |
| `LLM_BASE_URL` | `https://openrouter.ai/api/v1` | Replaceable OpenAI-compatible API root. |
| `OPENROUTER_API_KEY` / `LLM_API_KEY` | none | Secret bearer credential; never commit it. |
| `LLM_TIMEOUT_SECONDS` | `20` | Total bounded HTTP timeout. |
| `LLM_MAX_OUTPUT_TOKENS` | `700` | Maximum completion budget. |
| `LLM_TEMPERATURE` | `0` | Low-variance synthesis setting. |
| `LLM_HEALTH_CACHE_SECONDS` | `60` | Cache duration for the authenticated model probe. |
| `LLM_HTTP_REFERER` | local URL | Optional OpenRouter application attribution. |
| `LLM_APP_TITLE` | `PeopleOps Assistant` | Optional provider application title. |

For local use, copy `.env.example` to the ignored `.env`, set `LLM_PROVIDER=openrouter`, and add the
key there. Never paste a key into chat, a ticket, a screenshot, a command transcript, or a committed
file.

For Render:

1. Open **peopleops-assistant-demo > Environment**.
2. Add secret `OPENROUTER_API_KEY` with the key value.
3. Add `LLM_PROVIDER=openrouter`.
4. Keep the Blueprint-provided model, base URL, referer, and title or deliberately override them.
5. Save changes and wait for the service restart.
6. Confirm `/health.components.llm_provider.status` is `ready` without exposing the key.
7. Run **Actions > Hosted smoke > Run workflow** with `expected_llm_provider=openrouter` and the
   deployed SHA.

The corpus and all employee records are synthetic. Even so, only the minimum completed workflow
answer, decision fields, question, and cited snippets are sent to the provider. Free provider routes
may have lower availability and their own retention terms; never adapt this demo to real employee
data without a separate privacy, security, legal, and vendor review.

## Grounding and failure behavior

The provider is instructed to return JSON with `summary` and `citation_ids`. Acceptance requires:

1. the citation IDs exactly equal the workflow's verified evidence set;
2. the summary contains every exact `[POL-... § ...]` marker;
3. status, duration, category, approvals, and workflow-specific safety phrases remain present;
4. no new number, employee identifier, policy identifier, or section identifier appears;
5. the output remains within the bounded response length.

Accepted output is displayed above the unchanged **Verified workflow result**. Rejected or
unavailable output is never partially shown; `generation.mode=deterministic_fallback` explains that
the authoritative deterministic answer was returned. Clarifications, escalations, drafts, pending
actions, and confirmation-gated writes are never model-synthesized.

## Verification

```powershell
python -m pytest tests/test_llm_provider.py
python -m ruff check app/providers app/agent/orchestrator.py app/api/health.py

.\scripts\smoke_test_api.ps1 `
  -BaseUrl "https://peopleops-assistant-demo.onrender.com" `
  -ExpectedEnvironment production `
  -ExpectedReleaseSha "<deployed-sha>" `
  -ExpectedLlmProvider openrouter
```

Routine CI runs `LLM_PROVIDER=deterministic`, so pull requests do not depend on credentials, network
availability, rate limits, or paid inference. The production-provider smoke is a separate explicit
release check.
