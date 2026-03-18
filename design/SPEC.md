# Technical Specification

## Overview

SPF5000 V1 consists of:

- a Python FastAPI backend
- a React + TypeScript + Vite frontend
- a minimal `spf5000.toml` runtime config for host/port/paths/logging/session secret
- Google Photos Ambient API runtime credentials and sync cadence in `spf5000.toml`
- a cached weather and alert subsystem with a National Weather Service provider
- DecentDB for metadata, settings, display profiles, and import job history
- DecentDB-backed bootstrap state plus a single local admin user
- admin-protected ZIP backup/restore and collection media export workflows
- filesystem-backed originals and generated image variants
- provider-backed offline sync metadata for Google Photos auth/device/source state
- configurable background presentation modes for display, with cached color metadata plus render-time image-based treatments
- a fullscreen `/display` route optimized for kiosk playback on Raspberry Pi

The architecture follows the accepted ADR set in `design/adr/0001` through `0015` plus `0018`.

## Implemented architecture

### Backend responsibilities

- bootstrap runtime directories and DecentDB schema at startup
- load startup/runtime settings from `spf5000.toml`
- expose REST endpoints for setup, auth/session, health, status, settings, sources, collections, assets, uploads/imports, backup/export operations, and display state
- expose an authenticated sleep-schedule time-reference API so admin clients can compare server UTC, Pi-local timezone, and configured display timezone
- expose Google Photos provider APIs for device auth, status, disconnect, and sync triggers
- expose weather settings, weather status, weather alert, and display-facing weather APIs
- expose doctor/health diagnostics APIs for subsystem status and remediation guidance
- keep routes thin and place orchestration in services
- persist state through explicit repository SQL over the DecentDB DB-API binding
- manage local import, admin uploads, duplicate detection, original-file storage, and derivative generation
- manage database snapshot/export, validated database restore, collection media export, and the runtime coordination those workflows require
- manage Google Photos Ambient API device registration, media-source state, and background sync into the local asset pipeline
- manage scheduled weather and alert refresh into local cached state
- protect admin APIs with signed session cookies while keeping display APIs public
- serve built frontend assets from `frontend/dist` when available

### Frontend responsibilities

- provide a browser-based admin shell for configuration and diagnostics
- provide `/setup` and `/login` flows before the protected `/admin` shell
- provide a dedicated fullscreen `/display` route with no admin chrome
- provide a dedicated Backups page for database backup/restore and collection ZIP export
- provide a dedicated Doctor page for health diagnostics and troubleshooting
- consume backend API endpoints through typed helpers under `frontend/src/api/`
- keep display playback independent from the admin shell layout
- render configurable background presentation behind slideshow images using cached playlist metadata plus the display variant when needed
- render a configurable weather widget plus alert badge/banner/fullscreen overlays from cached backend data

### Persistence split

- DecentDB stores structured state and metadata
- DecentDB also stores bootstrap state and the single local admin record
- the filesystem stores original image binaries, generated display derivatives, generated thumbnails, staging data, and fallback assets
- database backup/restore operates on the DecentDB file, while collection export reads original media from the filesystem

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

Application settings such as slideshow timing, transition behavior, selected collection, sleep schedule, optional display timezone, bootstrap completion, and admin users remain in DecentDB.

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
- admin backup/restore workflows may create temporary files under `staging/backup-restore/` and `staging/exports/`

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
- `background_fill_mode`
- `display_timezone`
- `sleep_schedule_enabled`
- `sleep_start_local_time`
- `sleep_end_local_time`
- `weather_enabled`
- `weather_provider`
- `weather_location`
- `weather_units`
- `weather_position`
- `weather_refresh_minutes`
- `weather_show_precipitation`
- `weather_show_humidity`
- `weather_show_wind`
- `weather_alerts_enabled`
- `weather_alert_fullscreen_enabled`
- `weather_alert_minimum_severity`
- `weather_alert_repeat_enabled`
- `weather_alert_repeat_interval_minutes`
- `weather_alert_repeat_display_seconds`

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
- cached color metadata derived from display variants for color-based background modes
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

**Persistence model**: The `DisplayService.update_config()` method intentionally splits writes between two repositories:
- `settings_repo` — fields that affect the display pipeline (`slideshow_interval_seconds`, `transition_mode`, `transition_duration_ms`, `fit_mode`, `shuffle_enabled`, `selected_collection_id`, `background_fill_mode`, `shuffle_bag_enabled`). These are kept in `settings` because display pipeline code reads them from `SettingsRepository` at render time, avoiding a separate display profile lookup on every frame.
- `display_repo` — fields that are purely administrative or rarely changed (`name`, `idle_message`, `refresh_interval_seconds`). These belong in the display profile table.

This split is historical rather than logical; consolidating all display fields into `display_profiles` would simplify the service code but requires careful migration planning. See ADR 0013 for tracking.

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

### Weather tables

#### `weather_provider_state`

Current provider health and refresh metadata, including:

- provider status (`ready`, `degraded`, `disabled`, `unconfigured`)
- last attempted and last successful weather refresh timestamps
- last attempted and last successful alert refresh timestamps
- current provider error text

#### `weather_current_conditions`

Cached normalized current conditions for the configured location, including:

- condition summary and icon token
- canonical temperature value
- humidity, wind, and precipitation-chance details
- observation and fetch timestamps

#### `weather_alerts`

Cached normalized active alerts for the configured location, including:

- event, severity, certainty, and urgency
- headline, area, description, and instruction
- escalation mode and alert priority metadata
- issue/effective/expiry timestamps

#### `weather_refresh_runs`

Refresh history for weather and alert cache updates, including:

- refresh kind (`weather` or `alerts`)
- trigger (`scheduled` or `manual`)
- completion status and error text
- start and completion timestamps

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

## Backup and export workflows

1. `GET /api/backup/database/export` checkpoints and snapshots the active DecentDB file into a ZIP that includes `spf5000.ddb` plus `backup-manifest.json`.
2. `POST /api/backup/database/import` validates the uploaded ZIP structure, verifies that the bundled database looks like an SPF5000 database, pauses background coordinators, swaps the active `.ddb`, re-runs runtime initialization, resets connection state, and clears the current admin session.
3. `GET /api/backup/collections/{collection_id}/export` packages exportable original media files plus `collection-export-manifest.json`, skips missing or out-of-bounds originals, and fails only when no exportable originals remain.
4. Database restore does not restore original media files or generated variants; collection export is the media-moving path in V1.

## Google Photos provider and sync flow

1. The admin starts Google Photos connection from the Sources page.
2. SPF5000 starts the OAuth device flow and shows the Google verification code/URI.
3. After approval, SPF5000 registers an Ambient device and persists the returned `settingsUri`.
4. The admin opens the Google-managed `settingsUri` to choose what the frame should show.
5. The backend periodically syncs selected Google media into managed local storage and normalizes them into standard assets/variants.
6. `/display` continues to read only local playlist data and cached assets, even if Google is temporarily unavailable.

## Weather and alert subsystem

1. The admin configures a weather location, widget settings, and alert behavior from the Weather page.
2. A dedicated weather coordinator refreshes cached current conditions and active alerts on a schedule.
3. The provider normalizes remote payloads into SPF5000 weather and alert models before persistence.
4. `/api/display/weather` and `/api/display/alerts` expose only cached normalized state to the public display route.
5. `/display` renders weather and alert overlays without waiting on live provider requests.

## Display rendering strategy

### Route separation

- `/display` is intentionally independent from the admin shell
- the display route renders with a hidden cursor and a black fallback background
- the display route shows a calm idle state when no assets are available
- the display route can intentionally render a solid black fullscreen sleep state during the configured sleep window
- the display route can render a cached weather widget and alert overlays without changing slideshow layer ownership
- the display route can render `black`, `dominant_color`, `gradient`, `soft_vignette`, `palette_wash`, `blurred_backdrop`, `mirrored_edges`, or `adaptive_auto` background presentation behind the slideshow image when configured

### Dual-layer renderer

The slideshow uses two persistent absolutely positioned layers:

- one visible layer presents the current image
- one hidden layer preloads and decodes the next image
- motion begins only after the next image is ready
- the outgoing slide moves to the right while the incoming slide enters from the left
- the backing black background never becomes the intended transition state

Background treatment is rendered in separate persistent layers behind the slideshow image layers. Cached display-variant metadata remains the source for color-based modes such as `dominant_color`, `gradient`, `soft_vignette`, and `palette_wash`, and that metadata is persisted with asset records and lazily backfilled for older assets that predate the feature. Image-based treatments such as `blurred_backdrop` and `mirrored_edges` may reuse the display variant directly at render time.

`adaptive_auto` is a display-behavior policy. It chooses among supported treatments based on the current asset's aspect mismatch and the cached metadata available for that asset, favoring richer treatments when the data is ready and falling back to simpler supported options when it is not.

This preserves the ADR 0008 requirement to avoid a visible full-black frame between slides.

Scheduled sleep is the only intentional full-black display state. Entering or leaving sleep mode is separate from normal image-to-image transitions and does not relax the ADR 0008 transition rule.

### Scheduled sleep behavior

- the sleep schedule is stored in DecentDB-backed application settings, not in `spf5000.toml`, `systemd`, cron, or Chromium flags
- authenticated administrators manage the schedule and optional display timezone from the admin UI through dedicated sleep-schedule settings APIs
- `/api/display/playlist` includes the effective sleep schedule plus the configured display timezone so the public `/display` route can enforce it without requiring admin auth
- the display evaluates the schedule against the configured display timezone and falls back to the Pi-local timezone when no explicit display timezone is set
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
- background fill mode (`black`, `dominant_color`, `gradient`, `soft_vignette`, `palette_wash`, `blurred_backdrop`, `mirrored_edges`, or `adaptive_auto`)
- shuffle enabled/disabled
- selected collection
- idle message
- playlist refresh interval seconds
- sleep schedule enabled/disabled
- display timezone selection with Pi-local fallback
- sleep start and end times evaluated in the configured display timezone
- weather widget enabled/disabled
- weather widget position and units
- weather detail toggles for precipitation, humidity, and wind
- alert minimum severity, fullscreen allowance, and repeat cadence

### Weather and alert presentation

- the weather widget is a persistent overlay separate from slideshow layers
- banner and badge alerts stay outside the slideshow transition machinery
- fullscreen alerts pause slideshow timers instead of changing the dual-layer renderer itself
- `fullscreen_repeat` returns to a banner between repeated fullscreen takeovers
- sleep mode remains the highest-precedence display state

## Admin UI

The React admin shell currently includes:

- `/setup` for first-run bootstrap when no admin exists
- `/login` for returning administrators
- `/admin` as the protected shell root
- `Dashboard` for system/library status
- `Settings` for device and derivative defaults
- `Library` for batch uploading, filtering, and browsing imported assets and variants
- `Collections` for collection management
- `Backups` for database backup/restore plus collection media export
- `Sources` for local source configuration plus scan/import actions
- `Display Settings` for slideshow behavior, the sleep schedule, display timezone selection, and Pi-local/configured display-time clarity
- `Weather` for weather widget settings, provider/cache status, and alert visibility

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

### Weather

- `GET /api/weather/settings` (authenticated admin)
- `PUT /api/weather/settings` (authenticated admin)
- `GET /api/weather/status` (authenticated admin)
- `GET /api/weather/alerts` (authenticated admin)
- `POST /api/weather/refresh` (authenticated admin)

### Collections

- `GET /api/collections` (authenticated admin)
- `GET /api/collections/{collection_id}` (authenticated admin)
- `POST /api/collections` (authenticated admin)
- `PUT /api/collections/{collection_id}` (authenticated admin)

### Assets

- `GET /api/assets` (authenticated admin)
- `GET /api/assets/{asset_id}` (authenticated admin)
- `POST /api/assets/upload` (authenticated admin)
- `GET /api/assets/{asset_id}/variants/{kind}`

### Backup and export

- `GET /api/backup/database/export` (authenticated admin)
- `POST /api/backup/database/import` (authenticated admin)
- `GET /api/backup/collections/{collection_id}/export` (authenticated admin)

### Sources and import

- `GET /api/sources` (authenticated admin)
- `PUT /api/sources/{source_id}` (authenticated admin)
- `POST /api/import/local/scan` (authenticated admin)
- `POST /api/import/local/run` (authenticated admin)

### Display

- `GET /api/display/config` (authenticated admin)
- `PUT /api/display/config` (authenticated admin)
- `GET /api/display/playlist`
- `GET /api/display/weather`
- `GET /api/display/alerts`

## API Reference

### Authentication

All admin endpoints require an authenticated session. Obtain one via login, then include the session cookie in subsequent requests.

#### Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}' \
  -c cookies.txt
```

Response (200):
```json
{"username":"admin","bootstrapped":true,"user":{"username":"admin","is_admin":true}}
```

Error (401):
```json
{"detail":"Invalid username or password"}
```

#### Get current session
```bash
curl http://localhost:8000/api/auth/session -b cookies.txt
```

#### Logout
```bash
curl -X POST http://localhost:8000/api/auth/logout -b cookies.txt
```

### Health

#### Basic health check
```bash
curl http://localhost:8000/api/health
```
Response: `{"ok":true,"app":"SPF5000","version":"...","database_available":true}`

#### Deep health check (admin)
```bash
curl http://localhost:8000/api/health/deep -b cookies.txt
```
Response includes disk space, cache size, sync status, weather status, and asset count.

### Settings

#### Get settings (admin)
```bash
curl http://localhost:8000/api/settings -b cookies.txt
```

#### Update settings (admin)
```bash
curl -X PUT http://localhost:8000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"slideshow_seconds_per_image":10}' \
  -b cookies.txt
```

### Collections

#### List collections (admin)
```bash
curl http://localhost:8000/api/collections -b cookies.txt
```

#### Get collection (admin)
```bash
curl http://localhost:8000/api/collections/{collection_id} -b cookies.txt
```

### Assets

#### List assets (admin)
```bash
curl http://localhost:8000/api/assets -b cookies.txt
```

#### Upload asset (admin)
```bash
curl -X POST http://localhost:8000/api/assets/upload \
  -F "file=@photo.jpg" \
  -b cookies.txt
```

### Display

#### Get playlist (public)
```bash
curl http://localhost:8000/api/display/playlist
```
Response:
```json
{
  "items": [
    {
      "id": "uuid",
      "filename": "photo.jpg",
      "variant_url": "/api/assets/{id}/display"
    }
  ]
}
```

#### Get display weather (public)
```bash
curl http://localhost:8000/api/display/weather
```

### Error codes

| Code | Meaning |
|------|---------|
| 400  | Invalid request body or parameters |
| 401  | Missing or invalid session |
| 403  | Operation not permitted |
| 404  | Resource not found |
| 409  | Conflict (e.g., duplicate asset) |
| 422  | Validation error (Pydantic) |
| 429  | Rate limited |
| 500  | Internal server error |
| 503  | Service unavailable (no assets, etc.) |

Rate limit: 60 requests/minute per session on admin endpoints (enforced when `SPF5000_RATE_LIMIT=true`).

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
- the installer assumes an existing SPF5000 checkout, creates or refreshes `backend/.venv`, installs the DecentDB Python binding from the matching source archive, downloads the DecentDB native library from the matching release bundle, builds `frontend/dist`, generates a runtime `spf5000.toml`, installs the `systemd` unit, and installs the Chromium autostart entry for the selected non-root user
- default Pi runtime paths are `/opt/spf5000`, `/var/lib/spf5000`, `/var/cache/spf5000`, and `/var/lib/spf5000/spf5000.toml`
- the generated `systemd` unit runs `cd backend && .venv/bin/python -m app` with `SPF5000_CONFIG` pointing at the generated runtime config and `DECENTDB_NATIVE_LIB` pointing at the staged DecentDB C API library from the downloaded release bundle
- the generated Chromium autostart entry launches the local `/display` route in kiosk mode after a short startup delay
- `scripts/uninstall-pi.sh` removes the service and kiosk autostart while preserving config, database, cache, and imported assets by default
- `scripts/doctor.sh` checks runtime prerequisites, service state, filesystem paths, local health endpoints, display playlist/sleep state, first-slide asset reachability, and kiosk wiring

## Security posture

### Session cookies

Admin sessions are protected by signed HTTP-only cookies. The following configurations apply:

- **Development / local Pi**: `https_only = false` (default). Sessions work over plain HTTP. Appropriate for the localhost/LAN trust boundary of a home photo frame.
- **Production with reverse proxy**: Set `security.session_https_only = true` in `spf5000.toml` when the app runs behind a TLS-terminating reverse proxy (nginx, Caddy, etc.). This marks cookies as `Secure`, preventing transmission over plain HTTP.

### CSRF

The admin API uses signed session cookies with `allow_credentials=True` in CORS configuration. No explicit CSRF token is issued.

**Threat model**: SPF5000 is a LAN-only appliance. The admin interface is expected to be used from the same browser on the same device as the photo frame. Cross-site request forgery attacks require a malicious site visited by the same browser to forge requests to the local admin API — a low-probability scenario on a home network behind a router's NAT.

**Acceptance rationale**: CSRF protection adds complexity (token issuance, storage, validation) for a threat scenario that does not apply to this deployment model. The risk is accepted given the appliance's LAN-only, single-user nature. If the product is ever exposed beyond the LAN (e.g., via cloud sync), CSRF protection becomes mandatory before deployment.

### Input validation

All API inputs are validated by Pydantic schemas. File uploads are validated for image MIME type and extension before processing. DecentDB enforces a UNIQUE constraint on `assets.checksum_sha256` to prevent duplicate assets.

## Validation status

The current implementation has been validated with:

- `cd backend && .venv/bin/python -m pytest`
- `cd frontend && npm run build`

## Current limits

- local-files and Google Photos providers are implemented
- weather currently supports a single configured location and the National Weather Service provider
- admin batch uploads into local collections are supported, while destructive library management remains out of scope
- database backup/restore remains DB-only; moving original media still requires collection export or another filesystem-aware migration step
- v1 supports only a single local admin account with cookie-backed sessions
