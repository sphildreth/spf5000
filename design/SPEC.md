# Technical Specification

## Overview

SPF5000 V1 consists of:

- a Python FastAPI backend
- a React + TypeScript + Vite frontend
- a minimal `spf5000.toml` runtime config for host/port/paths/logging/session secret
- Google Photos Ambient API runtime credentials and sync cadence in `spf5000.toml`
- DecentDB for metadata, settings, display profiles, and import job history
- DecentDB-backed bootstrap state plus a single local admin user
- filesystem-backed originals and generated image variants
- provider-backed offline sync metadata for Google Photos auth/device/source state
- a fullscreen `/display` route optimized for kiosk playback on Raspberry Pi

The architecture follows the accepted ADR set in `design/adr/0001` through `0011`.

## Implemented architecture

### Backend responsibilities

- bootstrap runtime directories and DecentDB schema at startup
- load startup/runtime settings from `spf5000.toml`
- expose REST endpoints for setup, auth/session, health, status, settings, sources, collections, assets, imports, and display state
- expose Google Photos provider APIs for device auth, status, disconnect, and sync triggers
- keep routes thin and place orchestration in services
- persist state through explicit repository SQL over the DecentDB DB-API binding
- manage local import, duplicate detection, original-file storage, and derivative generation
- manage Google Photos Ambient API device registration, media-source state, and background sync into the local asset pipeline
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
- ensure default settings, default local and Google sources, default collections, the default display profile, and auth/bootstrap/provider tables exist

If the DecentDB binding is unavailable, the app preserves the existing `NullConnection` fallback path instead of crashing during import time.

## Runtime configuration

`spf5000.toml` is intentionally limited to startup/runtime concerns:

- bind host and port
- runtime storage paths
- log level
- optional session-cookie signing secret
- Google Photos OAuth client credentials and provider sync cadence

Application settings such as slideshow timing, transition behavior, selected collection, sleep schedule, bootstrap completion, and admin users remain in DecentDB.

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
    google-photos/
      import/
  staging/
    imports/
    google-photos/
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
- `sleep_schedule_enabled`
- `sleep_start_local_time`
- `sleep_end_local_time`

### `sources`

Configured provider sources. V1 seeds a default `local_files` source plus a Google Photos source used for offline-cached provider sync.

### `collections`

Logical groupings of imported assets. V1 seeds a default collection for local media plus an aggregate Google Photos collection for synced playback.

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

### `provider_auth_flows`

Persisted Google Photos device-code OAuth state, including verification URI, user code, polling cadence, and completion/error details.

### `provider_accounts`

Persisted provider account and device state, including linked Google identity metadata, access/refresh tokens, Google `settingsUri`, device polling guidance, and last sync timestamps.

### `provider_media_sources`

Persisted Google-managed media-source selections returned by the Ambient API device state.

### `provider_sync_runs`

Sync-run history for Google Photos provider activity, including import/duplicate/skipped/error counts and warning messages.

### `provider_assets`

Mappings from Google remote media IDs to locally managed SPF5000 assets and cached originals.

### `provider_asset_media_sources`

Join table mapping synced provider assets back to the Google media sources that surfaced them.

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

Providers implement the protocol in `backend/app/providers/base.py`. SPF5000 ships with `LocalFilesProvider` plus a Google Photos provider that uses the Ambient API device model and syncs media into the same local playback pipeline.

### Local import workflow

1. `POST /api/import/local/scan` scans the configured import directory recursively.
2. Supported image extensions are filtered using backend config.
3. `POST /api/import/local/run` imports discovered images.
4. SHA-256 checksum comparison prevents duplicate asset creation.
5. Managed original files are written to the filesystem.
6. Pillow extracts image metadata and generates display/thumbnail derivatives.
7. DecentDB records the asset, variants, collection membership, and job history.

Import failures do not stop the display route from continuing to run with the existing library.

## Google Photos provider and sync flow

1. The admin starts Google Photos connection from the Sources page.
2. SPF5000 starts the OAuth device flow and shows the Google verification code/URI.
3. After approval, SPF5000 registers an Ambient device and persists the returned `settingsUri`.
4. The admin opens the Google-managed `settingsUri` to choose what the frame should show.
5. The backend periodically syncs selected Google media into managed local storage and normalizes them into standard assets/variants.
6. `/display` continues to read only local playlist data and cached assets, even if Google is temporarily unavailable.

## Display rendering strategy

### Route separation

- `/display` is intentionally independent from the admin shell
- the display route renders on a black background with a hidden cursor
- the display route shows a calm idle state when no assets are available
- the display route can intentionally render a solid black fullscreen sleep state during the configured sleep window

### Dual-layer renderer

The slideshow uses two persistent absolutely positioned layers:

- one visible layer presents the current image
- one hidden layer preloads and decodes the next image
- motion begins only after the next image is ready
- the outgoing slide moves to the right while the incoming slide enters from the left
- the backing black background never becomes the intended transition state

This preserves the ADR 0008 requirement to avoid a visible full-black frame between slides.

Scheduled sleep is the only intentional full-black display state. Entering or leaving sleep mode is separate from normal image-to-image transitions and does not relax the ADR 0008 transition rule.

### Scheduled sleep behavior

- the sleep schedule is stored in DecentDB-backed application settings, not in `spf5000.toml`, `systemd`, cron, or Chromium flags
- authenticated administrators manage the schedule from the admin UI through dedicated sleep-schedule settings APIs
- `/api/display/playlist` includes the effective sleep schedule so the public `/display` route can enforce it without requiring admin auth
- the display evaluates the schedule against the local device time on the display hardware
- sleep start time is inclusive and sleep end time is exclusive, so the frame wakes at the configured end time
- overnight windows are supported
- when sleep is active, the display renders a solid black fullscreen overlay, pauses slideshow timers and transitions, and resumes playback automatically after the sleep window ends
- when the schedule is enabled, identical start and end times are rejected as invalid

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
- sleep schedule enabled/disabled
- sleep start and end times in local device time

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
- `Display Settings` for slideshow behavior and the sleep schedule

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
- `GET /api/settings/sleep-schedule` (authenticated admin)
- `PUT /api/settings/sleep-schedule` (authenticated admin)

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

### Pi appliance provisioning

- `scripts/install-pi.sh` is the first-pass Pi-specific installer for Raspberry Pi OS Desktop
- the installer assumes an existing SPF5000 checkout, creates or refreshes `backend/.venv`, validates the DecentDB Python binding, builds `frontend/dist`, generates a runtime `spf5000.toml`, installs the `systemd` unit, and installs the Chromium autostart entry for the selected non-root user
- default Pi runtime paths are `/opt/spf5000`, `/var/lib/spf5000`, `/var/cache/spf5000`, and `/var/lib/spf5000/spf5000.toml`
- the generated `systemd` unit runs `cd backend && .venv/bin/python -m app` with `SPF5000_CONFIG` pointing at the generated runtime config
- the generated Chromium autostart entry launches the local `/display` route in kiosk mode after a short startup delay
- `scripts/uninstall-pi.sh` removes the service and kiosk autostart while preserving config, database, cache, and imported assets by default
- `scripts/doctor.sh` checks runtime prerequisites, service state, filesystem paths, local health endpoints, and kiosk wiring

## Validation status

The current implementation has been validated with:

- `cd backend && .venv/bin/python -m pytest`
- `cd frontend && npm run build`

## Current limits

- only the local-files provider is implemented
- uploads, cloud providers, and destructive library management are not part of this pass
- v1 supports only a single local admin account with cookie-backed sessions
