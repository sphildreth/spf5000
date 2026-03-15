# Super Picture Frame 5000 (SPF5000)

SPF5000 is an offline-first, LAN-manageable digital picture frame stack for Raspberry Pi and similar Linux devices. V1 now ships a working FastAPI backend, a React + TypeScript + Vite frontend, DecentDB-backed metadata/state, filesystem-backed image storage, a local-files provider, and a dedicated fullscreen `/display` slideshow route with dual-layer slide transitions.

## What V1 includes

- FastAPI backend with startup bootstrap, health/status, settings, collections, assets, sources, import, and display endpoints
- DecentDB schema initialization on startup with explicit repository SQL
- `LocalFilesProvider` for scanning a configurable local import directory
- Duplicate detection by SHA-256 checksum
- Filesystem-backed originals plus generated `display` and `thumbnail` variants
- Admin UI pages for dashboard, settings, library, collections, sources/import, and display settings
- Fullscreen `/display` route with preload-before-transition behavior, hidden cursor, idle state, and no intentional black flash between images
- Static frontend serving from `frontend/dist` when the production build is present

## Repository layout

- `backend/` - FastAPI app, DecentDB bootstrap, repositories, services, providers, and tests
- `frontend/` - React + TypeScript + Vite admin and display UI
- `design/` - PRD, SPEC, ADR index, and accepted ADRs
- `scripts/` - convenience development/build helpers

## Quick start

### Backend

SPF5000 uses the real DecentDB Python binding, not a mock adapter. Install the backend dependencies first, then install DecentDB from a local checkout or other supported upstream source.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e /path/to/decentdb/bindings/python
uvicorn app.main:app --reload
```

If you cloned DecentDB next to this repository, a typical install command is:

```bash
cd backend
source .venv/bin/activate
python -m pip install -e ../decentdb/bindings/python
```

The backend listens on `http://127.0.0.1:8000` by default.

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

1. Open the admin UI at `/`.
2. Visit `Sources` and confirm the local import directory path.
3. Put supported images into the import directory.
4. Use `Scan` to preview what SPF5000 discovered.
5. Use `Import` to ingest assets, generate derivatives, and update the selected collection.
6. Tune slideshow behavior from `Display Settings`.
7. Open `/display` on the Pi-attached screen for fullscreen playback.

## Implemented API surface

- `GET /api/health`
- `GET /api/status`
- `GET /api/system/status`
- `GET|PUT /api/settings`
- `GET|POST /api/collections`
- `GET|PUT /api/collections/{collection_id}`
- `GET /api/assets`
- `GET /api/assets/{asset_id}`
- `GET /api/assets/{asset_id}/variants/{kind}`
- `GET /api/sources`
- `PUT /api/sources/{source_id}`
- `POST /api/import/local/scan`
- `POST /api/import/local/run`
- `GET|PUT /api/display/config`
- `GET /api/display/playlist`

## Raspberry Pi deployment notes

SPF5000 is designed for a Pi kiosk runtime:

- run the FastAPI backend locally on boot
- build the frontend with `cd frontend && npm run build`
- let FastAPI serve `frontend/dist`
- launch Chromium in kiosk/fullscreen mode against `http://127.0.0.1:8000/display`
- use another LAN device to access the admin UI at `http://<pi-hostname-or-ip>:8000/`

Example production-ish backend command:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Example kiosk launch target:

```bash
chromium --kiosk --app=http://127.0.0.1:8000/display
```

## Notes and current limits

- V1 is intentionally local-first and image-focused.
- The implemented provider is `LocalFilesProvider`; cloud providers and uploads are future work.
- Authentication is not part of this pass; the intended deployment model is a trusted local network.
- DecentDB remains the source of truth for metadata/settings, while the filesystem stores binaries and derivatives.
