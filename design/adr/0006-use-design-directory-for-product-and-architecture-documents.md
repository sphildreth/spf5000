# ADR 0006: Use `design/` Directory for Product and Architecture Documents

- Status: Accepted
- Date: 2026-03-15

## Context
The repository needs a clear separation between internal design artifacts and future end-user documentation. The original scaffold used `design/` for PRD, SPEC, and ADR content.

## Decision
Store product, specification, and architecture decision documents under `design/` and reserve `design/` for future user-friendly documentation.

## Consequences
- Internal architecture and planning artifacts remain clearly separated from user-facing documentation.
- Future tutorials, setup guides, and user manuals can live under `design/` without mixing audiences.
- Existing references to `design/` must be updated to `design/`.
