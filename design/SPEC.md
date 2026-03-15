# Technical Specification

## Overview

SPF5000 V1 consists of:

- a Python FastAPI backend
- a React + TypeScript + Vite frontend
- a minimal `spf5000.toml` runtime config for host/port/paths/logging/session secret
- DecentDB for metadata, settings, display profiles, and import job history
- DecentDB-backed bootstrap state plus a single local admin user
- filesystem-backed originals and generated image variants
- a fullscreen `/display` route optimized for kiosk playback on Raspberry Pi

The architecture follows the accepted ADR set in `design/adr/0001` through `0009`.

## Implemented architecture

### Backend responsibilities

- bootstrap runtime directories and DecentDB schema at startup
- load startup/runtime settings from `spf5000.toml`
- expose REST endpoints for setup, auth/session, health, status, settings, sources, collections, assets, imports, and display state
- keep routes thin and place orchestration in services
- persist state through explicit repository SQL over the DecentDB DB-API binding
- manage local import, duplicate detection, original-file storage, and derivative generation
- protect admin APIs with signed session cookies while keeping display APIs public
- serve built frontend assets from `frontend/dist` when available

### Frontend responsibilities

- provide a browser-based admin shell for configuration and diagnostics
- provide `/setup` and `/login` flows before the protected `/admin` shell
- provide a dedicated fullscreen `/display` route with no admin chrome
- consume backend API endpoints through typed helpers under `frontend/src/api/`
- keep display playback independent from the admin shell layout

### Persistence split

- DecentDB stores structured state and metadata
- DecentDB also stores bootstrap state and the single local admin record
- the filesystem stores original image binaries, generated display derivatives, generated thumbnails, staging data, and fallback assets

## Runtime model on Raspberry Pi

### Startup flow

1. Raspberry Pi OS boots into a lightweight graphical session.
2. The SPF5000 backend starts locally.
3. Backend startup reads `spf5000.toml`, initializes logging, directories, the DecentDB schema, and default records.
4. Chromium opens the local `/display` route in kiosk/fullscreen mode.
5. Administrators use a browser on the LAN to access `/setup`, `/login`, and `/admin`.

### Backend startup behavior

`backend/app/main.py` uses a FastAPI lifespan hook to:

- configure logging
- initialize storage directories
- create the fallback idle asset
- create missing DecentDB tables and indexes
- ensure default settings, the default local source, the default collection, the default display profile, and auth/bootstrap tables exist

If the DecentDB binding is unavailable, the app preserves the existing `NullConnection` fallback path instead of crashing during import time.

## Runtime configuration

`spf5000.toml` is intentionally limited to startup/runtime concerns:

- bind host and port
- runtime storage paths
- log level
- optional session-cookie signing secret

Application settings such as slideshow timing, transition behavior, selected collection, bootstrap completion, and admin users remain in DecentDB.

## Filesystem layout

Default backend-managed paths:

```text
backend/data/
  spf5000.ddb
  fallback/
    empty-display.jpg
  sources/
    local-files/
      import/
  staging/
    imports/
  storage/
    originals/
    variants/
      display/
      thumbnails/
```

### Storage rules

- imported originals are copied into managed storage
- display playback uses generated display derivatives rather than full originals
- admin pages use generated thumbnail derivatives
- deterministic filenames/paths are derived from asset metadata and checksums

## Data model

The V1 schema bootstraps these primary tables:

### `settings`

Key/value device settings, including:

- `frame_name`
- `display_variant_width`
- `display_variant_height`
- `thumbnail_max_size`
- `slideshow_interval_seconds`
- `transition_mode`
- `transition_duration_ms`
- `fit_mode`
- `shuffle_enabled`
- `selected_collection_id`
- `active_display_profile_id`

### `sources`

Configured provider sources. V1 seeds a default `local_files` source with the managed import path.

### `collections`

Logical groupings of imported assets. V1 seeds a default collection used by import and display flows.

### `assets`

Canonical imported image records, including:

- source ownership
- filename/original filename
- checksum
- dimensions and file size
- imported-from path
- managed original path
- metadata JSON
- imported timestamps
- active flag

### `asset_variants`

Generated derivatives keyed by asset and kind. V1 creates:

- `display`
- `thumbnail`

### `collection_assets`

Join table mapping assets into collections with stable sort order.

### `import_jobs`

Scan/import job history with discovered/imported/duplicate/skipped/error counters plus sample filenames and completion status.

### `display_profiles`

Persisted slideshow behavior, including:

- selected collection
- slideshow interval seconds
- transition mode
- transition duration milliseconds
- fit mode
- shuffle flag
- idle message
- playlist refresh interval seconds

### `admin_users`

The single local admin record, including:

- username
- password hash
- enabled flag
- last login timestamp

### `system_state`

Small key/value runtime metadata such as:

- bootstrap completion marker
- other system-level state that should stay in DecentDB

## Local provider and import flow

### Provider boundary

Providers implement the protocol in `backend/app/providers/base.py`. V1 includes `LocalFilesProvider` only, while preserving the abstraction boundary for future providers.

### Local import workflow

1. `POST /api/import/local/scan` scans the configured import directory recursively.
2. Supported image extensions are filtered using backend config.
3. `POST /api/import/local/run` imports discovered images.
4. SHA-256 checksum comparison prevents duplicate asset creation.
5. Managed original files are written to the filesystem.
6. Pillow extracts image metadata and generates display/thumbnail derivatives.
7. DecentDB records the asset, variants, collection membership, and job history.

Import failures do not stop the display route from continuing to run with the existing library.

## Display rendering strategy

### Route separation

- `/display` is intentionally independent from the admin shell
- the display route renders on a black background with a hidden cursor
- the display route shows a calm idle state when no assets are available

### Dual-layer renderer

The slideshow uses two persistent absolutely positioned layers:

- one visible layer presents the current image
- one hidden layer preloads and decodes the next image
- motion begins only after the next image is ready
- the outgoing slide moves to the right while the incoming slide enters from the left
- the backing black background never becomes the intended transition state

This preserves the ADR 0008 requirement to avoid a visible full-black frame between slides.

### Display settings

V1 supports these end-to-end settings:

- display duration in seconds
- transition duration in milliseconds
- transition type (`slide` today)
- fit mode (`contain` or `cover`)
- shuffle enabled/disabled
- selected collection
- idle message
- playlist refresh interval seconds

## Admin UI

The React admin shell currently includes:

- `/setup` for first-run bootstrap when no admin exists
- `/login` for returning administrators
- `/admin` as the protected shell root
- `Dashboard` for system/library status
- `Settings` for device and derivative defaults
- `Library` for browsing imported assets and variants
- `Collections` for collection management
- `Sources` for local source configuration plus scan/import actions
- `Display Settings` for slideshow behavior

Frontend API access stays under `frontend/src/api/` and uses relative `/api/...` paths so the Vite proxy works in development and the same routes work when FastAPI serves the production build.

Admin routing behavior:

- `/` redirects to `/setup`, `/login`, or `/admin` based on session/bootstrap state
- `/admin/*` requires an authenticated admin session
- `/setup` becomes unavailable once an enabled admin exists
- `/display` remains intentionally public and independent from the admin shell

## Implemented API surface

### Health and status

- `GET /api/health`
- `GET /api/status` (authenticated admin)
- `GET /api/system/status` (authenticated admin)

### Setup and auth

- `POST /api/setup`
- `GET /api/auth/session`
- `POST /api/auth/login`
- `POST /api/auth/logout`

### Settings

- `GET /api/settings` (authenticated admin)
- `PUT /api/settings` (authenticated admin)

### Collections

- `GET /api/collections` (authenticated admin)
- `GET /api/collections/{collection_id}` (authenticated admin)
- `POST /api/collections` (authenticated admin)
- `PUT /api/collections/{collection_id}` (authenticated admin)

### Assets

- `GET /api/assets` (authenticated admin)
- `GET /api/assets/{asset_id}` (authenticated admin)
- `GET /api/assets/{asset_id}/variants/{kind}`

### Sources and import

- `GET /api/sources` (authenticated admin)
- `PUT /api/sources/{source_id}` (authenticated admin)
- `POST /api/import/local/scan` (authenticated admin)
- `POST /api/import/local/run` (authenticated admin)

### Display

- `GET /api/display/config` (authenticated admin)
- `PUT /api/display/config` (authenticated admin)
- `GET /api/display/playlist`

## Development and deployment model

### Development

- backend launched with `cd backend && .venv/bin/python -m app`
- frontend Vite dev server on port `5173`
- Vite proxies `/api` to the backend

### Production

- build frontend assets into `frontend/dist`
- let FastAPI serve `frontend/dist`
- run the backend locally on the Pi
- provide a stable `spf5000.toml` (or `SPF5000_CONFIG`) for runtime deployment settings
- point Chromium kiosk mode at `http://127.0.0.1:8000/display`

## Validation status

The current implementation has been validated with:

- `cd backend && .venv/bin/python -m pytest`
- `cd frontend && npm run build`

## Current limits

- only the local-files provider is implemented
- uploads, cloud providers, and destructive library management are not part of this pass
- v1 supports only a single local admin account with cookie-backed sessions
