# Phase 8 evidence-first product interface

Phase 8 turns the bounded Phase 7 APIs into a reproducible grader-facing workspace. The interface
is a React/Vite application served by FastAPI in production and uses only the public `/health`,
`/chat`, and `/actions/mock-tickets/confirm` contracts.

## Interface map

| Area | Purpose | Evidence source |
|---|---|---|
| Header | Product identity, synthetic-data warning, selected employee | Local presentation data aligned to the committed synthetic seed |
| Demo-task rail | One-click remote-work, PTO, expense, and ticket scenarios | Versioned Phase 7 workflow prompts |
| System health | Current component status, application version, environment | Live `/health` response |
| Conversation | User request, bounded outcome, answer, counts, request ID, trace ID | Live `/chat` response |
| Employee context | Role, department, manager, location, employment, PTO snapshot | Presentation subset of committed synthetic records |
| Citation inspector | Policy/section IDs, snippets, versions, effective dates, format, pages, chunk IDs, scores | Validated citation objects returned by `/chat` |
| Tool-trace inspector | Ordered MCP calls, sanitized arguments, summaries, status, errors, duration | Sanitized operational trace returned by `/chat` |
| Confirmation dialog | Exact mock-ticket preview, synthetic warning, cancel/confirm decision | Pending action plus confirmation endpoint |

The interface never queries the corpus, database, or MCP server directly. It does not display or
approximate hidden reasoning. All operational evidence comes from typed API fields.

## Grader walkthrough

1. Open the application and confirm the blue **Synthetic demo environment** banner.
2. Check **System health** in the left rail. The API, corpus, RAG index, MCP, and mock database
   should report ready; the optional provider may truthfully report not configured.
3. In **International remote work**, select **Run task**.
4. Confirm the result is conditional and inspect four exact citations, eight MCP operations,
   request ID, trace ID, employee context, and fixed as-of date.
5. Run **PTO request guidance**. Confirm the result is labelled draft-only and the message is not
   represented as sent.
6. Run **Expense compliance**. Confirm the cap, employee-paid remainder, approval path, citations,
   and tool trace are visible.
7. Run **Confirmation-gated ticket**. Inspect the action preview and verify that the trace contains
   no create call. Select **Cancel** to prove the action remains pending, then reopen it with
   **Review pending action**.
8. Select **Confirm mock ticket**. Confirm the final response identifies the synthetic ticket and
   the trace now contains one `create_mock_hr_ticket` call. The signed token is never rendered.

## Control behavior

- **Load** places a task in the composer without making an API request.
- **Run task** selects the correct employee and immediately runs the versioned prompt.
- The header employee selector changes the composer context and the employee context panel.
- **New chat** and **Ask another question** clear the current response without mutating data.
- **Copy guidance** copies the answer plus request and trace identifiers when clipboard access is
  available.
- Citation and trace panels use native expandable controls, including on narrow screens.
- The confirmation dialog focuses the primary decision, supports Escape/cancel, and reuses the
  original request ID, employee, and message after confirmation.
- Health refresh, network failures, clarifications, escalations, denied actions, and timeouts remain
  visible controlled states.

## Responsive and accessibility behavior

The desktop layout uses task, conversation, and evidence columns. At tablet widths the evidence
inspectors move below the conversation. At mobile widths the task rail becomes compact navigation,
context cards stack, inspector panels remain expandable, and no horizontal overflow is introduced.

The page uses semantic landmarks, labelled fields, visible keyboard focus, an ARIA live conversation
region, an ARIA modal confirmation dialog, text labels in addition to color, and native details/
summary disclosure controls.

## Automated verification

`ui/src/App.test.tsx` verifies:

1. workspace identity, health, demo tasks, evidence panels, and employee context;
2. loading a preset without invoking a workflow;
3. cited workflow rendering with citation, trace, request ID, and trace ID;
4. explicit confirmation followed by request-bound creation; and
5. cancellation that leaves the write-like action blocked.

Run:

```powershell
Set-Location ui
npm run test
npm run build
```

The normal repository check and CI pipeline run these checks alongside backend, contract, corpus,
RAG, MCP, workflow, and container verification.

## Phase boundary

Phase 8 completes the product interface. Phase 9 will harden CI/CD and deployment operations,
including startup and hosted smoke coverage, dependency-action maintenance, and release evidence.
