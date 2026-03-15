# Architecture Repository Document

This repository uses Architecture Decision Records (ADRs) to capture important technical and product design decisions over time.

## Why ADRs

ADRs are used because they preserve:

- the decision that was made
- the context at the time
- the alternatives considered
- the consequences of the decision

This makes the system easier to maintain long-term, especially after future refactors or changes in technology preferences.

## ADR Conventions

- ADR files live in `design/adr/`
- file naming pattern: `NNNN-title.md`
- statuses: Proposed, Accepted, Superseded, Deprecated
- every meaningful architectural deviation should result in a new ADR rather than editing history away

## Initial ADR Set

- 0001-use-fastapi-for-backend.md
- 0002-use-react-typescript-vite-for-frontend.md
- 0003-use-decentdb-for-metadata-and-settings.md
- 0004-use-filesystem-for-image-binaries.md
- 0005-use-provider-abstraction-for-photo-sources.md
- 0006-use-design-directory-for-product-and-architecture-documents.md
- 0007-use-browser-kiosk-runtime-on-pi.md
- 0008-use-dual-layer-slideshow-renderer-with-slide-transition.md
