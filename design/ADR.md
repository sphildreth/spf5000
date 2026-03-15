# Architecture Repository Document

This repository uses Architecture Decision Records (ADRs) to capture durable technical and product decisions over time.

## Why ADRs

ADRs preserve:

- the decision that was made
- the context at the time
- the alternatives considered
- the consequences of the decision

That history is especially important for SPF5000 because runtime, persistence, and display behavior are intentionally constrained by accepted design choices.

## ADR conventions

- ADR files live in `design/adr/`
- filenames use `NNNN-title.md`
- statuses include `Proposed`, `Accepted`, `Superseded`, and `Deprecated`
- meaningful architectural deviations should be captured in a new ADR rather than rewriting accepted history away

## Accepted ADR set

- `0001-use-fastapi-for-backend.md` - backend framework choice
- `0002-use-react-typescript-vite-for-frontend.md` - frontend stack choice
- `0003-use-decentdb-for-metadata-and-settings.md` - structured local persistence choice
- `0004-use-filesystem-for-image-binaries.md` - image binary and derivative storage boundary
- `0005-use-provider-abstraction-for-photo-sources.md` - source/provider integration boundary
- `0006-use-design-directory-for-product-and-architecture-documents.md` - documentation source-of-truth layout
- `0007-use-browser-kiosk-runtime-on-pi.md` - Pi runtime model
- `0008-use-dual-layer-slideshow-renderer-with-slide-transition.md` - display pipeline and transition strategy

## V1 implementation status

The current V1 implementation is expected to conform to ADRs `0001` through `0008`:

- FastAPI remains the backend entrypoint and API host
- React + TypeScript + Vite remain the frontend stack
- DecentDB remains the metadata/settings store
- the filesystem remains responsible for originals and generated image variants
- providers remain behind a protocol boundary, with `LocalFilesProvider` implemented first
- the Pi runtime model remains browser-kiosk based
- `/display` remains a dedicated dual-layer slideshow route that avoids an intentional black frame between transitions

No additional ADR was required during this implementation pass because the work clarified and implemented the accepted architecture rather than changing it.
