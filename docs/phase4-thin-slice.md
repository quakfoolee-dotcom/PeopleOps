# Phase 4 thin vertical slice

## Delivered path

Phase 4 implements one intentionally bounded workflow:

```text
POST /chat
  -> PeopleOpsOrchestrator
  -> official MCP Client: tools/list
  -> lookup_employee_profile
  -> search_policy_documents
  -> ChatResponse with citations and sanitized tool_trace
```

The orchestrator imports neither the policy corpus reader nor the synthetic-data store. Only the
MCP tool implementation can read those sources. This architectural constraint makes the MCP
integration genuine rather than a display-only trace.

The MCP server is mounted at `/mcp` using Streamable HTTP. Its two Phase 4 tools are also exercised
in-memory by integration tests through the same official MCP protocol implementation. The remaining
six planned contracts are implemented in Phase 6.

## Reproduce the successful use case

Start the combined service:

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Send the fixed demonstration request:

```powershell
$body = @{
    employee_id = "E-1007"
    message = "Can I work remotely from Germany for six weeks?"
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "http://127.0.0.1:8000/chat" `
    -ContentType "application/json" `
    -Body $body
```

Expected outcome:

- `status=completed` and `outcome=conditional`;
- employee facts for synthetic employee E-1007;
- citations for `INT-4`, `INT-5`, `INT-13`, and `RWK-5`;
- trace order `mcp_discover_tools`, `lookup_employee_profile`,
  `search_policy_documents`;
- no write, email, ticket, or external provider call.

The same flow is available in the web interface. Open the application, keep the E-1007 preset,
and select **Run cited workflow**.

## Failure and boundary use cases

| Case | Expected behavior |
|---|---|
| Employee ID omitted | Clarification response; no MCP call |
| Unknown employee E-9999 | Employee lookup is traced; policy search is not called |
| Unsupported PTO or expense prompt | Out-of-scope response; no MCP call |
| Date differs from 2026-09-01 | Clarification response; no MCP call |
| MCP endpoint unavailable | Error and escalation response; no invented facts or citations |
| Required MCP tool missing | Error and escalation response naming a sanitized discovery failure |
| Policy evidence insufficient | Escalation response; no policy rule is inferred |

## Phase boundary

`search_policy_documents` uses a deterministic keyword route for the single international
remote-work demonstration. It extracts content from stable policy sections and returns structured
citation metadata, but it is not the Phase 5 retrieval engine. Format-aware ingestion, chunking,
embeddings, keyword indexing, hybrid ranking, evidence sufficiency, and citation validation remain
Phase 5 work.

## Automated evidence

- `tests/test_phase4_mcp.py` proves discovery and both invocations through the official MCP client.
- `tests/test_phase4_chat.py` proves the orchestrated response, HTTP contract, trace order, and
  failure behavior.
- `ui/src/App.test.tsx` proves the preset sends `/chat` and renders citation and trace evidence.
- `scripts/check.ps1` runs backend lint/schema/asset/tests, frontend tests/build, and Docker build.
