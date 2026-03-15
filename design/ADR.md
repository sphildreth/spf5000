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
- `0009-use-runtime-config-and-single-admin-bootstrap-auth.md` - runtime config, bootstrap flow, and admin auth boundary
- `0010-use-pi-specific-appliance-installer-toolchain.md` - Pi deployment automation strategy
- `0011-use-app-managed-sleep-schedule-for-display-quiet-hours.md` - app-managed display quiet-hours behavior

## V1 implementation status

The current V1 implementation is expected to conform to ADRs `0001` through `0011`:

- FastAPI remains the backend entrypoint and API host
- React + TypeScript + Vite remain the frontend stack
- DecentDB remains the metadata/settings store
- the filesystem remains responsible for originals and generated image variants
- providers remain behind a protocol boundary, with `LocalFilesProvider` implemented first
- the Pi runtime model remains browser-kiosk based
- Pi deployment automation remains intentionally Pi-specific, Bash-based, and centered on `systemd`, Chromium autostart, and runtime health checks
- `/display` remains a dedicated dual-layer slideshow route that avoids an intentional black frame between transitions
- scheduled sleep behavior remains app-managed, DecentDB-backed, and enforced by `/display` with a black fullscreen sleep state instead of OS-level shutdown or blanking
- `spf5000.toml` owns startup/runtime concerns while DecentDB remains the source of truth for settings, bootstrap state, and the local admin record
- `/setup`, `/login`, `/admin`, and the signed session-cookie model define the admin auth boundary while keeping `/display` public
