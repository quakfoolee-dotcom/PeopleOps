# Phase 8 evidence-first product interface

Phase 8 turns the bounded Phase 7 APIs into a reproducible grader-facing workspace. The interface
is a React/Vite application served by FastAPI in production and uses only the public `/health`,
`/chat`, `/attachments/extract`, and `/actions/mock-tickets/confirm` contracts.

## Interface map

| Area | Purpose | Evidence source |
|---|---|---|
| Header | Product identity, synthetic-data warning, selected employee | Local presentation data aligned to the committed synthetic seed |
| Functional navigation and demo-task rail | Chat, collapsible demo tasks, highlighted employee context, interactive help, and synthetic employee switching | Local presentation data and versioned bounded-workflow prompts |
| System health | MCP connectivity, RAG index, mock database, LLM provider, application version, environment, last-check time, and release identity | Live `/health` response plus client refresh time |
| Conversation | User request, structured decision, answer, next steps, compact policy sources, and available actions | Live `/chat` response |
| Composer | Natural-language question, optional use-case routing hint, and bounded TXT/Markdown/PDF attachment | `/attachments/extract` followed by `/chat` |
| Employee context | Role, department, manager, location, employment, PTO snapshot | Presentation subset of committed synthetic records |
| Citation inspector | Policy/section IDs, snippets, versions, effective dates, format, pages, chunk IDs, scores | Validated citation objects returned by `/chat` |
| Tool-trace inspector | Ordered MCP calls, sanitized arguments, summaries, status, errors, duration, counts, request ID, and trace ID | Sanitized operational trace returned by `/chat` |
| Confirmation dialog | Exact mock-ticket preview, synthetic warning, cancel/confirm decision | Pending action plus confirmation endpoint |

The interface never queries the corpus, database, or MCP server directly. It does not display or
approximate hidden reasoning. All operational evidence comes from typed API fields.

## Grader walkthrough

1. Open the application and confirm the blue **Synthetic demo environment** banner.
2. Check **System health** in the left rail. `MCP Connectivity`, `RAG Index`, `Mock Database`, and
   `LLM Provider` should report healthy. Confirm the explicit **App Version**, **Last checked**, and
   shortened **Release** rows. The `/health` link exposes the complete application and policy-corpus
   detail. The provider reports healthy when configured, not configured when deliberately disabled,
   or unavailable when its sanitized health probe fails.
3. In **International remote work**, select **Run task**.
4. Confirm the card separately shows conditional status, 42 calendar/30 business days,
   `International exceptional`, required approvals, exact-date clarification, and ordered next
   steps. Inspect four exact citations, eight MCP operations, request ID, trace ID, employee
   context, labelled generation mode/provider, and the demo policy as-of date.
5. Select **Generate draft email**. Confirm the bounded workflow calls `draft_hr_email` and renders
   a dedicated card with recipient, subject, readable body paragraphs, and an explicit **Not sent**
   state. Copying or regenerating the draft must not send or persist anything.
6. Run **PTO request guidance**. Review the balance and policy result, then select **Generate draft
   email**. Confirm the manager-addressed draft appears in the same structured card without changing
   the PTO balance.
7. Run **Expense compliance**. Confirm the cap, employee-paid remainder, approval path, citations,
   and tool trace are visible.
8. Run **Confirmation-gated ticket**. Inspect the action preview and verify that the trace contains
   no create call. Select **Cancel** to prove the action remains pending, then reopen it with
   **Review pending action**.
9. Select **Confirm mock ticket**. Confirm the final response identifies the synthetic ticket and
   the trace now contains one `create_mock_hr_ticket` call. The signed token is never rendered.
10. Run **Policy and benefits guidance**. Confirm the answer cites `POL-BEN-001 BEN-5`; the trace
    contains policy search and exact-section retrieval but no employee-profile or benefits-status
    lookup. The preset intentionally sends no employee ID.

## Control behavior

- **Load** places a task in the composer without making an API request.
- **Run task** selects the correct employee when required and immediately runs the versioned prompt.
  The general policy/benefits task is explicitly employee-neutral.
- **Employee Context** scrolls to the combined profile, PTO, benefits, manager, location, and
  employment panel and provides a visible selected-navigation and target highlight.
- **Help** opens an accessible product-guidance dialog. Its sample questions prepare the composer
  and use-case hint without sending a request.
- **Switch Employee** opens a labelled selector with a live profile preview. The header selector
  remains available and both controls update the composer context and employee context panel.
- Navigation does not advertise request history, settings, or other destinations that the demo does
  not implement.
- **New chat** and **New question** clear the current response without mutating data.
- **Save conversation** copies the answer plus request and trace identifiers when clipboard access is
  available.
- The optional use-case selector provides a routing hint; the bounded classifier and safety gates
  remain authoritative.
- **Attach file** accepts TXT, Markdown, or PDF up to 2 MB. The server extracts at most 6,000
  characters without persistence. Attachment text can fill missing request facts only when it
  resolves the selected workflow; it never replaces the authoritative policy corpus.
- **Generate draft email** is shown for eligible remote-work and PTO guidance. It runs the existing
  MCP draft tool in the background while preserving the verified guidance and request context.
- Generated drafts use a dedicated card with recipient, subject, paragraph-preserving body, safety
  notice, **Copy draft**, and **Regenerate draft** controls. The API and UI both keep them explicitly
  unsent and non-persistent.
- **Re-run** controls repeat the exact employee-bound request. Unsupported or decorative workflow
  actions are not displayed.
- Citation and trace panels use native expandable controls, including on narrow screens.
- The confirmation dialog focuses the primary decision, supports Escape/cancel, and reuses the
  original request ID, employee, and message after confirmation.
- Health refresh updates the visible local **Last checked** time. Network failures, missing primary
  components, clarifications, escalations, denied actions, and timeouts remain visible controlled
  states.

## Responsive and accessibility behavior

The desktop layout uses task, conversation, and evidence columns. At tablet widths the evidence
inspectors move below the conversation. At mobile widths the rail becomes compact navigation, the
collapsible task list remains operable in a bounded scroll region, context cards stack, inspector
panels remain expandable, and no horizontal overflow is introduced.

The page uses semantic landmarks, labelled fields, visible keyboard focus, an ARIA live conversation
region, an ARIA modal confirmation dialog, text labels in addition to color, and native details/
summary disclosure controls.

## Automated verification

`ui/src/App.test.tsx` verifies:

1. workspace identity, health, demo tasks, evidence panels, and employee context;
2. functional task collapse, Help prompt selection, employee-context navigation, and employee switching;
3. loading a preset without invoking a workflow;
4. structured decision, approvals, clarification, next steps, compact sources, trace, and identifiers;
5. use-case and attachment extraction/submission behavior;
6. the real MCP-backed remote-work and PTO structured draft actions, including recipient, subject,
   body, safety state, copy, and regeneration controls;
7. explicit confirmation followed by request-bound creation; and
8. cancellation that leaves the write-like action blocked.

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
