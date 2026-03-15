# Super Picture Frame 5000 (SPF5000)

SPF5000 is an offline-first, LAN-manageable digital picture frame platform for Raspberry Pi and similar Linux devices. It is designed to avoid subscription fees, vendor lock-in, opaque cloud dependencies, and fragile mobile-app-only administration.

This starter repository provides:

- A FastAPI backend scaffold
- A React + TypeScript + Vite frontend scaffold
- DecentDB-first architecture notes and repository layout
- Product documentation including PRD, SPEC, and ADRs
- Basic provider and sync abstractions for future Google Photos and local storage integration

## Repo layout

- `backend/` - FastAPI application, services, repositories, and API endpoints
- `frontend/` - React + TypeScript + Vite admin/display UI
- `docs/` - PRD, SPEC, and architecture decision records
- `scripts/` - convenience scripts for development and deployment

## Intended v1 scope

- Fullscreen display page for slideshow playback
- Local admin UI for frame settings and diagnostics
- Local file management on device
- Source/provider model for future Google Photos ambient integration
- Metadata and settings persisted in DecentDB
- Image files cached on local disk

## Quick start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Notes

This is a starter scaffold, not a finished product. Many service implementations are intentionally stubbed so the project can evolve with ADR-backed decisions instead of accidental architecture.
