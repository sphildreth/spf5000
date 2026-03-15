# Technical Specification

## Overview
SPF5000 consists of a Python FastAPI backend, a React + TypeScript + Vite frontend, local image cache storage, and DecentDB for metadata/state persistence.

## High-Level Architecture

### Backend Responsibilities
- expose REST API for administration and display state
- manage providers and sync orchestration
- manage local image catalog and metadata
- persist settings and sync state in DecentDB
- serve built frontend assets if deployed as single service

### Frontend Responsibilities
- admin UI for settings, sources, albums, and media management
- display UI for fullscreen slideshow playback
- consume backend API over local network

### Persistence Responsibilities
- DecentDB stores structured metadata
- filesystem stores image binaries and generated variants

## Proposed Directory Layout

```text
backend/
  app/
    api/
    core/
    db/
    models/
    repositories/
    schemas/
    services/
    providers/
    main.py
frontend/
  src/
    api/
    components/
    features/
    layouts/
    pages/
    styles/
design/
  adr/
```

## Data Model

### settings
Stores device-wide settings such as slideshow interval, fit mode, source selection defaults, sleep hours, and display preferences.

### photo_sources
Stores configured source providers such as local disk, Google Photos Ambient, NAS import, or future providers.

### albums
Stores logical display groups and mappings to provider collections.

### assets
Stores metadata about each known image.

Suggested columns:
- id
- source_id
- album_id
- provider_asset_id
- filename
- mime_type
- width
- height
- checksum_sha256
- origin_type
- local_original_path
- local_display_path
- created_utc
- updated_utc
- is_active

### sync_jobs
Stores sync runs, state, duration, and outcomes.

### sync_events
Stores detailed sync log items suitable for UI diagnostics.

## Backend Modules

### `core/config.py`
Application settings using `pydantic-settings`.

### `db/connection.py`
DecentDB connection factory and repository transaction helper.

### `repositories/`
Thin persistence layer with explicit SQL.

### `services/`
Business logic and orchestration.

### `providers/`
Source integrations implementing a common interface.

## API Surface (initial)

### Health
- `GET /api/health`
- `GET /api/system/status`

### Settings
- `GET /api/settings`
- `PUT /api/settings`

### Media
- `GET /api/media`
- `POST /api/media/upload`
- `DELETE /api/media/{id}`

### Albums
- `GET /api/albums`
- `POST /api/albums`
- `PUT /api/albums/{id}`
- `DELETE /api/albums/{id}`

### Sources
- `GET /api/sources`
- `POST /api/sources`
- `POST /api/sources/{id}/sync`

### Display
- `GET /api/display/playlist`

## Provider Interface

```python
class PhotoProvider(Protocol):
    def provider_name(self) -> str: ...
    def health_check(self) -> dict: ...
    def list_collections(self) -> list[dict]: ...
    def sync_collection(self, collection_id: str) -> dict: ...
```

## Frontend Structure

### Display App
- fullscreen slideshow route
- polls or refreshes playlist periodically
- minimal UI chrome

### Admin App
- dashboard shell
- settings editor
- source status cards
- album/media management pages

## Deployment Model

### Development
- FastAPI runs separately on port 8000
- Vite dev server runs separately on port 5173

### Production
- frontend built into static assets
- FastAPI serves built frontend from `frontend/dist`
- systemd unit starts backend on boot
- browser opens fullscreen display page on local HDMI session

## Logging and Diagnostics
- structured backend logs to stdout and rotating file
- sync event history persisted in DecentDB
- basic status endpoint for UI and future watchdogs

## Security
- v1 assumes trusted LAN administration
- admin token or simple local auth may be added later
- no public internet exposure required for core operation

## Open Questions
- exact Google Photos Ambient onboarding sequence
- whether image resizing should be synchronous, background worker, or first-view lazy generation
- whether display should be fully browser-based or allow a future native renderer
