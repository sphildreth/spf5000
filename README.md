# Super Picture Frame 5000 (SPF5000)

SPF5000 is an offline-first, LAN-manageable digital picture frame stack for Raspberry Pi and similar Linux devices. V1 now ships a FastAPI backend, a React + TypeScript + Vite frontend, DecentDB-backed metadata/state, filesystem-backed image storage, a local-files provider, a minimal `spf5000.toml` runtime config, single-admin bootstrap/login flows, and a dedicated fullscreen `/display` slideshow route with dual-layer slide transitions.

## What V1 includes

- FastAPI backend with runtime config loading, startup bootstrap, auth/session, health/status, settings, collections, assets, sources, import, and display endpoints
- DecentDB schema initialization on startup with explicit repository SQL
- `LocalFilesProvider` for scanning a configurable local import directory
- Duplicate detection by SHA-256 checksum
- Filesystem-backed originals plus generated `display` and `thumbnail` variants
- First-run `/setup` flow that creates the single local admin account
- Session-cookie auth for `/login`, `/admin`, and protected admin APIs
- Admin UI pages for dashboard, settings, library, collections, sources/import, and display settings under `/admin`
- Fullscreen `/display` route with preload-before-transition behavior, hidden cursor, idle state, and no intentional black flash between images
- Static frontend serving from `frontend/dist` when the production build is present

## Repository layout

- `backend/` - FastAPI app, DecentDB bootstrap, repositories, services, providers, and tests
- `frontend/` - React + TypeScript + Vite admin and display UI
- `design/` - PRD, SPEC, ADR index, and accepted ADRs
- `deploy/` - Pi deployment templates for `systemd`, Chromium autostart, and runtime config examples
- `scripts/` - convenience development/build helpers plus Pi install, uninstall, and doctor scripts

## Quick start

### Backend

SPF5000 uses the real DecentDB Python binding, not a mock adapter. Install the backend dependencies first, then install DecentDB from a local checkout or other supported upstream source.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e /path/to/decentdb/bindings/python
python -m app
```

If you cloned DecentDB next to this repository, a typical install command is:

```bash
cd backend
source .venv/bin/activate
python -m pip install -e ../../decentdb/bindings/python
```

The backend reads runtime settings from repo-root `spf5000.toml` by default. Override the config file path with `SPF5000_CONFIG=/path/to/spf5000.toml`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server listens on `http://127.0.0.1:5173` and proxies `/api` to the backend.

### Validation

```bash
cd backend
.venv/bin/python -m pytest

cd ../frontend
npm run build
```

## Runtime configuration

SPF5000 keeps startup/runtime concerns in `spf5000.toml` and keeps application settings, bootstrap state, and admin user records in DecentDB.

The checked-in `spf5000.toml` demonstrates the supported structure for development, and `deploy/config/spf5000.toml.example` shows the recommended Pi appliance layout:

```toml
[server]
host = "0.0.0.0"
port = 8000
debug = false

[paths]
data_dir = "./backend/data"
cache_dir = "./backend/cache"
database_path = "./backend/data/spf5000.ddb"

[logging]
level = "INFO"
```

Use `SPF5000_CONFIG` to point the backend at a different config file. Session signing uses `security.session_secret` when provided; otherwise SPF5000 generates an ephemeral secret and invalidates admin sessions on restart.

## Runtime and storage layout

By default the backend creates and manages these paths:

- `backend/data/spf5000.ddb` - DecentDB metadata and settings
- `backend/data/storage/originals/` - managed original image copies
- `backend/data/storage/variants/display/` - slideshow-sized display derivatives
- `backend/data/storage/variants/thumbnails/` - admin thumbnails
- `backend/data/sources/local-files/import/` - default local-files import/watch directory
- `backend/data/fallback/empty-display.jpg` - idle fallback backing asset

Originals and variants use deterministic managed paths derived from imported asset metadata and checksums.

## Admin workflow

1. Open `/` from a browser on the LAN.
2. On a fresh install, complete `/setup` to create the single admin account.
3. After bootstrap, sign in at `/login` and use the admin shell under `/admin`.
4. Visit `Sources` and confirm the local import directory path.
5. Put supported images into the import directory.
6. Use `Scan` to preview what SPF5000 discovered.
7. Use `Import` to ingest assets, generate derivatives, and update the selected collection.
8. Tune slideshow behavior from `Display Settings`.
9. Open `/display` on the Pi-attached screen for fullscreen playback.

## Implemented API surface

- `GET /api/health`
- `POST /api/setup`
- `GET /api/auth/session`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/status` (authenticated admin)
- `GET /api/system/status` (authenticated admin)
- `GET|PUT /api/settings` (authenticated admin)
- `GET|POST /api/collections` (authenticated admin)
- `GET|PUT /api/collections/{collection_id}` (authenticated admin)
- `GET /api/assets` (authenticated admin)
- `GET /api/assets/{asset_id}` (authenticated admin)
- `GET /api/assets/{asset_id}/variants/{kind}`
- `GET /api/sources` (authenticated admin)
- `PUT /api/sources/{source_id}` (authenticated admin)
- `POST /api/import/local/scan` (authenticated admin)
- `POST /api/import/local/run` (authenticated admin)
- `GET|PUT /api/display/config` (authenticated admin)
- `GET /api/display/playlist`

## Raspberry Pi deployment notes

SPF5000 is designed for a Pi kiosk runtime:

- run the FastAPI backend locally on boot
- provide a stable `spf5000.toml` (or `SPF5000_CONFIG`) for bind/path/session-secret settings
- build the frontend with `cd frontend && npm run build`
- let FastAPI serve `frontend/dist`
- launch Chromium in kiosk/fullscreen mode against `http://127.0.0.1:8000/display`
- use another LAN device to access bootstrap/login/admin at `http://<pi-hostname-or-ip>:8000/`

Example production-ish backend command:

```bash
cd backend
source .venv/bin/activate
SPF5000_CONFIG=/var/lib/spf5000/spf5000.toml python -m app
```

Example kiosk launch target:

```bash
chromium --kiosk --app=http://127.0.0.1:8000/display
```

For Raspberry Pi OS Desktop, the repository now includes a first-pass appliance installer toolchain:

```bash
sudo ./scripts/install-pi.sh --user pi
sudo ./scripts/doctor.sh --user pi
```

The installer provisions apt packages, `backend/.venv`, `frontend/dist`, a runtime config under `/var/lib/spf5000`, the `spf5000.service` unit, and the Chromium autostart entry for the selected user. It defaults to `--host 0.0.0.0` so the admin UI stays reachable on the LAN while Chromium still targets the local `/display` route.

To remove the appliance wiring without deleting photos or database state:

```bash
sudo ./scripts/uninstall-pi.sh --user pi
```

See `docs/PI_SETUP_GUIDE.md` for the Pi OS prep steps and `docs/INSTALLER.md` for the installer workflow, managed files, and troubleshooting commands.

## Notes and current limits

- V1 is intentionally local-first and image-focused.
- The implemented provider is `LocalFilesProvider`; cloud providers and uploads are future work.
- Authentication is intentionally single-admin and local-account only; multi-user and external identity providers are future work.
- DecentDB remains the source of truth for metadata/settings, while the filesystem stores binaries and derivatives.
