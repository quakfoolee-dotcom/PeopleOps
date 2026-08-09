# UI design decision for the Score-5 workspace

## Decision

The evidence-first wireframe is implemented as the Phase 8 product workspace. Its information
architecture is backed by the completed RAG, MCP, workflow, safety, and action contracts rather than
static demonstration placeholders.

The implementation combines:

- the wireframe's demo tasks, employee context, compliance result, citation inspector, MCP trace,
  request/trace identifiers, real service status, and confirmation panel; and
- the current interface's Northstar visual language, responsive layout, accessible focus states,
  live regions, and truthful backend-driven status.

## Required corrections

- E-1007 is Alex Morgan, Senior Data Analyst, with registered Vancouver home office data.
- The primary demonstration is six weeks in Germany, normally about 30 business days in the
  `International exceptional` category.
- Policy metadata comes from corpus version 1.0, effective 2026-09-01.
- Health indicators always come from `/health`; unfinished services may not be displayed as ready.
- Controls and navigation are hidden until functional; the final product has no dead links.
- The operational trace contains actual MCP events, not hidden reasoning or fabricated future steps.
- Both request ID and trace ID are visible.
- Mock ticket creation uses an explicit confirmation token and idempotency key.
- Citation, trace, and context panels collapse into accessible drawers or tabs on smaller screens.

## Phase 5 contract influence

Phase 5 citations now provide the panel-ready policy ID, section ID, title, snippet, version,
effective date, source format/path, PDF page when applicable, stable chunk ID, and retrieval score.
This prevents the Phase 8 interface from inventing presentation metadata or re-querying the corpus
directly.

## Phase 8 verification

The interface provides four reproducible tasks, truthful `/health` state, request and trace IDs,
employee context, exact citation metadata, the full sanitized MCP trace, responsive disclosure
panels, and a keyboard-accessible confirmation dialog. Five frontend interaction tests cover the
shell, task loading, grounded output, confirmed creation, and cancel-without-create behavior. See
`docs/phase8-product-interface.md` for the grader walkthrough.
