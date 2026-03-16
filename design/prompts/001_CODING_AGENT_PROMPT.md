# SPF5000 V2 Coding Agent Prompt

You are implementing **SPF5000 (Super Picture Frame 5000)**.

This repository already contains the starter structure, product/design documentation, and ADRs. Your job is to implement **V1** in a disciplined, production-minded way that aligns with the documented architecture.

## Required reading before making changes

Read these first and treat them as authoritative:

- `README.md`
- `PRD.md`
- `SPEC.md`
- `ADR.md`
- `design/adr/0001-use-fastapi-for-backend.md`
- `design/adr/0002-use-react-typescript-vite-for-frontend.md`
- `design/adr/0003-use-decentdb-for-local-persistence.md`
- `design/adr/0004-use-provider-based-photo-source-architecture.md`
- `design/adr/0005-store-image-binaries-on-filesystem-and-metadata-in-db.md`
- `design/adr/0006-use-design-directory-for-product-and-architecture-documents.md`
- `design/adr/0007-use-browser-kiosk-runtime-on-pi.md`
- `design/adr/0008-use-dual-layer-slideshow-renderer-with-slide-transition.md`

If code conflicts with documentation/ADRs, update code to match the docs unless you find a serious defect. If you find a serious defect in the docs, update the relevant ADR/SPEC and explain why in your final summary.

---

## High-level goal

Implement a working **local-first Pi-hosted digital picture frame** with:

- FastAPI backend
- React + TypeScript + Vite frontend
- DecentDB for metadata/settings/state
- local filesystem storage for image assets and derivatives
- fullscreen slideshow display route
- browser-based admin UI
- provider abstraction with **Local Files** implemented first
- runtime model designed for Raspberry Pi kiosk mode

The display experience is critical:

- fullscreen
- smooth
- no black flashes between images
- left-to-right slide transition preferred by the target audience
- appliance-like behavior

---

## Non-negotiable architectural requirements

1. **Backend**: Python + FastAPI
2. **Frontend**: React + TypeScript + Vite
3. **Persistence**: DecentDB, not SQLite
4. **Asset storage**: filesystem, not BLOB-heavy DB storage
5. **Display runtime on Pi**: browser kiosk model
6. **Display renderer**: dual-layer slideshow renderer
7. **Transition behavior**: left-to-right slide transition with no visible blank screen
8. **Documentation discipline**: update ADR/SPEC/ADR/README when architectural decisions or behavior become more concrete

---

## Scope for this implementation pass

Implement a usable V1 with the following:

### 1. Backend foundation
Create a maintainable FastAPI backend with:

- app startup/shutdown lifecycle
- configuration system
- logging
- API routing structure
- health endpoint
- settings endpoints
- asset/library endpoints
- slideshow/display endpoints
- static file serving support if needed

Suggested backend shape:

- `backend/app/main.py`
- `backend/app/core/`
- `backend/app/api/`
- `backend/app/db/`
- `backend/app/repositories/`
- `backend/app/services/`
- `backend/app/providers/`
- `backend/app/models/`
- `backend/app/schemas/`

Keep modules small and obvious.

### 2. DecentDB integration
Implement a small but real DecentDB integration layer.

Requirements:

- central DB initialization
- schema bootstrap on startup
- repository pattern over direct scattered SQL
- explicit SQL preferred
- no fake ORM abstraction unless necessary

Persist at minimum:

- app/device settings
- albums/collections
- assets metadata
- asset variants metadata
- source/provider metadata
- slideshow/display profile settings
- sync/import job history

Be honest about the exact DecentDB Python API used. Match the installed package version and do not invent methods.

### 3. Local provider implementation
Implement the first provider:

- `LocalFilesProvider`

This provider should support:

- scanning an import/watch directory
- discovering supported image files
- assigning assets to a default collection/album
- updating metadata/index state in DecentDB
- generating derivatives for display/admin use

Keep provider abstraction clean so future providers can include:

- Google Photos Ambient/API-based provider
- NAS folder providers
- SMB/NFS-backed sources
- upload provider

### 4. Filesystem storage design
Use the filesystem for image storage.

Implement clear directory conventions for:

- originals
- display derivatives
- thumbnails
- temp/import staging
- fallback assets

Prefer deterministic paths and filenames derived from asset IDs/hashes.

### 5. Display route and slideshow engine
Implement `/display` as the fullscreen slideshow page.

This is the most important user-facing route.

Requirements:

- dedicated display route with no admin chrome
- dual-layer rendering strategy
- preload next image fully before transition
- no black frame between transitions
- smooth left-to-right slide transition
- configurable display duration and transition duration
- configurable fit mode (`contain` and `cover` at minimum)
- support shuffle and deterministic order modes
- black background behind content
- hidden cursor
- stable layout with no jarring reflow

Implementation guidance:

- use two absolutely positioned visual layers
- keep current image visible while next image preloads and decodes
- transition only after next image is ready
- when complete, reuse the now-hidden layer for the next preload
- avoid single-image `src` swapping

It is acceptable to begin with image-only support.

### 6. Admin UI
Implement a small React admin UI with practical pages:

- dashboard/status
- settings
- library/assets
- albums/collections
- import/local source management
- slideshow/display settings

Keep UI clean and simple.

Do not over-design.

### 7. Import management
Support at least one practical import path in V1.

Minimum acceptable implementation:

- admin-configurable local import directory
- backend scan/import action
- basic duplicate detection
- derivative generation on import

Optional if time permits:

- direct browser upload UI

### 8. Slideshow settings
Support these settings end-to-end:

- display duration seconds
- transition duration ms
- transition type (initially just `slide-left` and optionally `cut`)
- shuffle on/off
- fit mode (`contain` / `cover`)
- selected collection/album
- idle/fallback behavior when library is empty

### 9. Status and resilience
Implement basic operational resilience:

- health endpoint
- simple status endpoint for UI
- meaningful logs
- clear error states in admin UI
- slideshow should keep running even if imports fail
- display should show a tasteful idle/empty state when no assets exist

---

## Pi runtime assumptions

The implementation should assume this deployment shape:

- Raspberry Pi boots into a lightweight graphical session
- browser launches fullscreen/kiosk to local SPF5000 display URL
- FastAPI backend runs locally on the Pi
- admin UI is reachable from other LAN devices
- display UI is local and fullscreen on the Pi-attached monitor

You do **not** need to fully implement OS/service scripts unless they are already scaffolded, but you should:

- document expected runtime behavior
- include sample `systemd` unit files and kiosk launch scripts if reasonable
- keep config values ready for local deployment

---

## UX requirements for the display route

The target audience strongly prefers:

- calm slideshow behavior
- images smoothly sliding in horizontally
- no black gaps between images
- no obvious "browser app" feel

Therefore:

- prioritize smoothness over flashy effects
- do not add fancy transitions beyond what is required
- do not show spinners during normal playback
- do not show debug text on the display route

The slideshow should feel like an appliance, not a dashboard.

---

## Frontend guidance

Use React + TypeScript + Vite.

Recommended structure:

- `frontend/src/app/`
- `frontend/src/pages/`
- `frontend/src/components/`
- `frontend/src/features/display/`
- `frontend/src/features/admin/`
- `frontend/src/lib/`
- `frontend/src/api/`
- `frontend/src/styles/`

Prefer:

- small components
- simple state management
- clear data-fetching layer
- CSS modules or straightforward scoped CSS approach

Avoid bringing in heavyweight UI frameworks unless clearly justified.

A small internal design system is fine:

- buttons
- forms
- panels/cards
- status badges
- simple layout primitives

---

## Backend guidance

Prefer:

- explicit service layer
- explicit repositories
- Pydantic schemas for API contracts
- typed settings/config
- clear startup initialization flow

Avoid:

- hidden magic
- giant god-services
- overengineering for future providers not yet implemented

---

## API expectations

Implement clean endpoints for:

- health/status
- settings get/update
- collections/albums list
- assets list/detail
- local import scan/run
- slideshow config
- playlist retrieval for display route

Reasonable examples include:

- `GET /api/health`
- `GET /api/status`
- `GET /api/settings`
- `PUT /api/settings`
- `GET /api/collections`
- `GET /api/assets`
- `POST /api/import/local/scan`
- `POST /api/import/local/run`
- `GET /api/display/config`
- `PUT /api/display/config`
- `GET /api/display/playlist`

These do not have to match exactly if you choose a better layout, but keep the API obvious and internally consistent.

---

## Data model guidance

At minimum, model these concepts:

- `settings`
- `source`
- `collection`
- `asset`
- `asset_variant`
- `import_job`
- `display_profile`

Suggested semantics:

### asset
Represents a canonical imported image.

Fields might include:

- id
- source_id
- collection_id
- original_filename
- original_path
- mime_type
- width
- height
- checksum
- created_at
- updated_at
- imported_at
- captured_at (nullable)
- active flag

### asset_variant
Represents derived files.

Fields might include:

- id
- asset_id
- kind (`thumbnail`, `display`)
- path
- width
- height
- file_size
- created_at

### display_profile
Represents slideshow behavior.

Fields might include:

- id
- name
- selected_collection_id
- transition_type
- transition_ms
- display_seconds
- fit_mode
- shuffle_enabled
- enabled

---

## Image processing guidance

Generate derivatives during import.

At minimum:

- thumbnail derivative for admin UI
- display derivative sized appropriately for the target monitor class

Do not always render huge originals directly in the slideshow.

Design the derivative generation so target display resolution can be configurable later.

---

## Documentation requirements

Update documentation as part of implementation.

Required updates:

- `README.md`
- `SPEC.md`
- `ADR.md`
- relevant ADRs if implementation clarifies decisions

If you make a new architectural decision, add a new ADR in:

- `design/adr/`

Also update any ADR index or cross-references.

---

## Quality bar

Deliver something that is:

- coherent
- runnable with reasonable setup
- clearly structured
- honest about placeholders and future work
- aligned to the repo docs

Do not fake completeness.

If something cannot be fully implemented in one pass, leave:

- clear TODOs
- explicit comments
- documented next steps

But do implement as much working end-to-end functionality as possible.

---

## Nice-to-have items if time permits

- browser upload UI
- asset delete/archive flow
- simple album assignment UI
- basic slideshow preview in admin UI
- sample systemd service files
- sample kiosk startup script
- example `.env.example`
- initial test coverage for repositories/services

---

## Out of scope for this pass

Do not spend major time on:

- Google Photos integration
- cloud sync
- authentication/authorization complexity
- video support
- advanced multi-user features
- remote internet exposure
- mobile app

Design for these later, but do not implement them now.

---

## Completion checklist

Before finishing, verify:

- backend starts cleanly
- frontend builds cleanly
- display route works and uses dual-layer transitions
- no black flash between image changes
- local provider can import at least one directory of images
- DecentDB schema bootstrap works
- docs reflect reality
- any new ADRs are added if needed

---

## Final response format

When done, provide:

1. Summary of what was implemented
2. What remains incomplete
3. Any assumptions made
4. Any ADRs added/updated
5. Exact commands to run backend and frontend locally
6. Exact commands or notes for Pi deployment if applicable

Be precise, structured, and honest.
