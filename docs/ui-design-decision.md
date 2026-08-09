# UI design decision for the Score-5 workspace

## Decision

The new evidence-first wireframe is the target information architecture for Phase 8. The deployed
Phase 4 interface remains the working product until the RAG, tool, and workflow contracts needed by
the new workspace are complete.

The final implementation will combine:

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
