<p align="center">
  <img src="graphics/logo-1024x1024.png" alt="SPF5000 logo" width="220" />
</p>

<h1 align="center">Super Picture Frame 5000</h1>

<p align="center">
  <strong>Offline-first digital picture frame software for Raspberry Pi.</strong><br />
  FastAPI backend, React + TypeScript admin UI, DecentDB metadata, filesystem-backed images, and a polished fullscreen <code>/display</code> experience.
</p>

<p align="center">
  <a href="#quick-start">Quick start</a>
  ·
  <a href="#raspberry-pi-appliance-deployment">Pi deployment</a>
  ·
  <a href="#development">Development</a>
  ·
  <a href="#documentation">Documentation</a>
</p>

<p align="center">
  <img alt="Release 1.0.0" src="https://img.shields.io/badge/release-1.0.0-2563eb?style=flat-square" />
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img alt="React 19 + Vite" src="https://img.shields.io/badge/react-19%20%2B%20vite-61DAFB?style=flat-square&logo=react&logoColor=111827" />
  <img alt="Raspberry Pi kiosk runtime" src="https://img.shields.io/badge/raspberry%20pi-kiosk%20runtime-C51A4A?style=flat-square&logo=raspberrypi&logoColor=white" />
  <img alt="License Apache 2.0" src="https://img.shields.io/badge/license-Apache%202.0-4b5563?style=flat-square" />
</p>

SPF5000 is a self-hosted, LAN-manageable digital picture frame stack for Raspberry Pi-class hardware. It is built for households that want an appliance-like frame without subscriptions, vendor lock-in, fragile mobile apps, cloud dependency, or visible black flashes between slides.
<details>
<summary>Table of contents</summary>

- [✨ Key Features](#-key-features)
- [Architecture at a glance](#architecture-at-a-glance)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Raspberry Pi appliance deployment](#raspberry-pi-appliance-deployment)
- [Development](#development)
- [API and UX surface](#api-and-ux-surface)
- [Project structure](#project-structure)
- [Documentation](#documentation)
- [Current limits](#current-limits)
- [Contributing](#contributing)
- [License](#license)

</details>

## ✨ Key Features

SPF5000 exists to make a digital picture frame feel like a dependable home appliance instead of a subscription service. Here are the highlights of what's inside:

- 🔌 **Offline-First by Design** — Playback stays local and cached instead of depending on live cloud responses.
- 🖼️ **Appliance-Oriented UX** — The Pi boots directly into a dedicated, gorgeous fullscreen slideshow at `/display`.
- 🚀 **Smooth Transitions** — Say goodbye to jarring black flashes! The display route uses a dual-layer renderer that preloads the next image before animating.
- 🎨 **Expanded Background Presentation** — Portrait and mixed-aspect slides support `black`, `dominant_color`, `gradient`, `soft_vignette`, `palette_wash`, `blurred_backdrop`, `mirrored_edges`, and `adaptive_auto`; cached display-variant metadata drives color-based modes while image-based treatments can reuse the display variant at render time.
- 📱 **LAN-Managed Admin** — Setup, login, settings, import, and diagnostics are seamlessly available from a browser on your local network.
- 🧳 **Backup & Export Ready** — Download ZIP backups of the DecentDB state, restore validated database backups, and export original collection media without dropping to SSH.
- ☁️ **Google Photos Integration** — First-class Google Photos provider using the Ambient API for offline-cached local playback.
- 🌦️ **Weather & Alerts** — Built-in National Weather Service integration for real-time widget overlays and fullscreen alerts.
- 🛠️ **Modern Stack** — Built with a snappy **FastAPI backend** and a polished **React 19 + TypeScript + Vite frontend**.
- 🔒 **Secure & Private** — Single-admin session auth, clear storage boundaries with **DecentDB**, and locally managed files with SHA-256 duplicate detection.
- 🌙 **Smart Scheduling** — App-managed sleep schedule stored in DecentDB, evaluated in a configurable display timezone with Pi-local fallback, and surfaced in the admin UI with both Pi-local and display-time clocks.
- 🍓 **Pi-Ready** — Includes appliance scripts for install, uninstall, and health checks on Raspberry Pi OS Desktop.
- 🔍 **Doctor Page** — Built-in health diagnostics page that aggregates subsystem status, identifies problems, and provides actionable remediation guidance.

## Architecture at a glance

### Core stack

- **Backend:** FastAPI
- **Frontend:** React 19 + TypeScript + Vite
- **Structured state:** DecentDB
- **Binary storage:** local filesystem
- **Display runtime:** Chromium kiosk mode on Raspberry Pi

### Runtime flow

```text
Local import folder      Google Photos Ambient API
        │                         │
        ▼                         ▼
LocalFilesProvider      GooglePhotosProvider
        │                         │
        └──────────────► import / sync services
                                  │
                ┌─────────────────┴─────────────────┐
                ▼                                   ▼
      DecentDB metadata/settings/bootstrap   Filesystem originals +
                state                        display/thumbnail variants
                                                        │
                                                        ▼
                                              /api/display/playlist
                                                        │
                                                        ▼
                                          Chromium kiosk at /display
```

### Display behavior

The fullscreen `/display` route is intentionally separate from the admin shell. It stays public, runs without admin chrome, uses a hidden cursor, preloads the next slide before transitioning, supports configurable `black`, `dominant_color`, `gradient`, `soft_vignette`, `palette_wash`, `blurred_backdrop`, `mirrored_edges`, and `adaptive_auto` background presentation, keeps cached display-variant metadata as the source for color-based modes, may reuse the display variant directly for image-based modes, and can render an intentional black fullscreen sleep state during configured quiet hours evaluated in the configured display timezone or the Pi-local timezone when none is set.

Weather and alert overlays are also display concerns, but they still follow the same appliance rules: weather and alerts are fetched and cached by the backend, `/display` consumes only cached data, and sleep mode remains the highest-precedence fullscreen state.

## Quick start

### Prerequisites

- Python `3.11+`
- Node.js and npm
- for source-based local development, a local **DecentDB checkout** so you can install the Python binding and build the native library

SPF5000 does **not** install DecentDB from `backend/requirements.txt`. You must make both the editable Python binding and the native library available separately.
For local development in this repo, the expected DecentDB path is still a source checkout. The Raspberry Pi appliance installer uses a different path: it downloads the latest matching release bundle for the native library and the matching source archive for the Python binding.

### 1. Start the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e /path/to/decentdb/bindings/python
cd /path/to/decentdb
nimble build_lib
export DECENTDB_NATIVE_LIB=$PWD/build/libc_api.so
cd /path/to/spf5000/backend
python -m app
```

If you cloned `decentdb` next to this repository, a typical install looks like this:

```bash
cd backend
source .venv/bin/activate
python -m pip install -e ../../decentdb/bindings/python
cd ../../decentdb
nimble build_lib
export DECENTDB_NATIVE_LIB=$PWD/build/libc_api.so
cd ../spf5000/backend
python -m app
```

When running from a DecentDB source checkout, `build/libc_api.so` is the normal Linux output. Release bundles may instead ship `libdecentdb.so`; the Python binding accepts either filename, and `DECENTDB_NATIVE_LIB` can point to either one.

The backend reads `spf5000.toml` from the repo root by default. Override the config path with `SPF5000_CONFIG=/path/to/spf5000.toml`.

### 2. Start the frontend dev server

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs on `http://127.0.0.1:5173` and proxies `/api` to the backend on port `8000`.

### 3. Open the app

- **Dev UI:** `http://127.0.0.1:5173`
- **Backend API docs:** `http://127.0.0.1:8000/api/docs`
- **Production-style UI after a frontend build:** `http://127.0.0.1:8000`

On a fresh install, the root app flow sends you through `/setup` first so you can create the single local admin account.

### 4. Validate your environment

```bash
cd backend
.venv/bin/python -m pytest

cd ../frontend
npm run build
```

## Configuration

SPF5000 keeps startup and runtime wiring in `spf5000.toml`. Application settings such as slideshow timing, selected collection, bootstrap completion, admin credentials, the display sleep schedule, and the optional display timezone live in DecentDB.

Example config:

```toml
[server]
host = "0.0.0.0"
port = 8000
debug = false

[logging]
level = "INFO"

[security]
# session_secret = "replace-with-a-long-random-string"

[paths]
data_dir = "./backend/data"
cache_dir = "./backend/cache"
database_path = "./backend/data/spf5000.ddb"

[providers.google_photos]
# Google Photos Ambient API OAuth client for TVs and limited-input devices.
client_id = "your-google-client-id"
client_secret = "your-google-client-secret"
provider_display_name = "Google Photos"
sync_cadence_seconds = 3600
```

Important notes:

- Set `SPF5000_CONFIG` to use a different runtime config path.
- Set `security.session_secret` if you want admin sessions to survive backend restarts.
- If `security.session_secret` is omitted, SPF5000 generates an ephemeral secret and admin sessions are invalidated on restart.
- Sleep scheduling and the optional display timezone are managed in-app and stored in DecentDB, not in `cron`, `systemd`, Chromium flags, or `spf5000.toml`.
- Google Photos credentials live in `spf5000.toml`, while linked-account state, selected media sources, sync runs, and provider asset mappings live in DecentDB.
- Google Photos playback stays offline-first: the frame syncs media into managed local storage and `/display` plays from the local cache.
- Weather settings, cached conditions, active alerts, and refresh history live in DecentDB-backed application state rather than the runtime config file.

### Default managed storage layout

By default, the backend manages these paths:

- `backend/data/spf5000.ddb`
- `backend/data/fallback/empty-display.jpg`
- `backend/data/sources/local-files/import/`
- `backend/data/sources/google-photos/import/`
- `backend/data/staging/imports/`
- `backend/data/staging/google-photos/`
- `backend/data/storage/originals/`
- `backend/data/storage/variants/display/`
- `backend/data/storage/variants/thumbnails/`

### Supported image formats

The backend currently recognizes:

- `.jpg`
- `.jpeg`
- `.png`
- `.webp`
- `.gif`

## Raspberry Pi appliance deployment

SPF5000 is designed around a browser-kiosk runtime on **Raspberry Pi OS Desktop**.

Recommended hardware and OS:

- Raspberry Pi 3 or Raspberry Pi 4
- Raspberry Pi OS with Desktop

The supported appliance flow is:

1. the Pi boots into the desktop automatically
2. the backend starts as a `systemd` service
3. Chromium launches in kiosk mode against local `/display`
4. administrators manage the frame from another device on the LAN

### Quick Pi install path

```bash
sudo raspi-config
sudo raspi-config nonint do_blanking 1

sudo mkdir -p /opt
cd /opt
sudo git clone https://github.com/sphildreth/spf5000.git
sudo chown -R pi:pi /opt/spf5000

cd /opt/spf5000
sudo ./scripts/install-pi.sh --user pi
sudo ./scripts/doctor.sh --user pi

sudo reboot
```

Then from another device on the LAN:

```text
http://<pi-hostname-or-ip>:8000/setup
```

### What the installer manages

`scripts/install-pi.sh` automates:

- apt package installation for the supported Pi runtime
- `backend/.venv` creation and backend dependency installation
- DecentDB binding installation from the matching source archive plus native-library download from the matching release bundle
- `frontend/dist` creation
- runtime `spf5000.toml` generation
- `systemd` service installation and startup
- Chromium autostart kiosk wiring

Useful companion scripts:

- `scripts/doctor.sh` — validates service state, local health checks, display playlist/sleep state, Chromium availability, and kiosk wiring
- `scripts/uninstall-pi.sh` — removes appliance wiring while preserving data by default

For full appliance details, read:

- [`docs/PI_SETUP_GUIDE.md`](docs/PI_SETUP_GUIDE.md)
- [`docs/INSTALLER.md`](docs/INSTALLER.md)

## Development

Backend commands assume `backend/.venv` exists; activate it or use `.venv/bin/python` explicitly. Frontend commands assume `cd frontend && npm install` has already been run.

### Common commands

| Task | Command |
| --- | --- |
| Start backend | `make backend` |
| Start frontend dev server | `make frontend` |
| Run backend tests | `make test` |
| Run one backend test | `cd backend && .venv/bin/python -m pytest tests/test_health.py::test_health` |
| Build the frontend | `cd frontend && npm run build` |
| Preview the frontend build | `cd frontend && npm run preview` |
| Start backend via helper script | `./scripts/dev-backend.sh` |
| Start frontend via helper script | `./scripts/dev-frontend.sh` |
| Build frontend via helper script | `./scripts/build-frontend.sh` |

### Production frontend serving

When `frontend/dist` exists, FastAPI serves the built frontend directly. That lets a single backend process expose:

- the admin UI
- the setup/login flow
- the public `/display` route
- the API under `/api`

## API and UX surface

### User-facing routes

- `/setup` — first-run bootstrap flow
- `/login` — returning admin sign-in
- `/admin` — protected admin shell
- `/display` — public fullscreen slideshow route

### Main API groups

- health and system status
- setup and auth/session
- settings, display timezone, and sleep schedule
- weather settings, cached conditions, and alert status
- collections and assets
- backup, restore, and collection export workflows
- sources and local import
- display config, public playlist, and public weather/alert overlays

Browse the generated OpenAPI docs at:

```text
http://127.0.0.1:8000/api/docs
```

## Project structure

```text
backend/    FastAPI app, services, repositories, providers, tests
frontend/   React + TypeScript + Vite admin and display UI
design/     PRD, SPEC, ADR index, accepted architecture decisions
docs/       Raspberry Pi setup, backup/export, Google Photos, and installer guides
deploy/     systemd, autostart, and config templates
graphics/   project artwork and logos
scripts/    development and Pi appliance helper scripts
```

## Documentation

Design and operational docs live in-repo:

- [`design/PRD.md`](design/PRD.md) — product goals and scope
- [`design/SPEC.md`](design/SPEC.md) — technical specification
- [`design/ADR.md`](design/ADR.md) — architecture decision record index
- [`design/adr/`](design/adr/) — accepted and proposed ADRs
- [`CHANGELOG.md`](CHANGELOG.md) — release notes following Keep a Changelog
- [`docs/PI_SETUP_GUIDE.md`](docs/PI_SETUP_GUIDE.md) — end-to-end Pi setup
- [`docs/BACKUP_AND_EXPORT_GUIDE.md`](docs/BACKUP_AND_EXPORT_GUIDE.md) — database backup/restore and collection media export workflows
- [`docs/GOOGLE_PHOTOS_GUIDE.md`](docs/GOOGLE_PHOTOS_GUIDE.md) — Google Photos credential setup, connection flow, and sync behavior
- [`docs/INSTALLER.md`](docs/INSTALLER.md) — installer, doctor, and uninstall details

## Current limits

SPF5000 `1.0.0` is intentionally focused:

- Google Photos selection happens through Google's Ambient settings UI instead of an in-app full-library browser
- weather currently supports one configured location and the U.S. National Weather Service provider
- browser uploads support batch image ingestion into local collections
- database backup and restore cover DecentDB state only; original media still requires collection export or other filesystem migration
- destructive library management remains intentionally limited
- authentication is single-admin and local-account only
- the product is image-focused; video-first playback is not a goal for this version

## Contributing

Issues and pull requests are welcome.

Before making large changes:

1. read [`design/PRD.md`](design/PRD.md), [`design/SPEC.md`](design/SPEC.md), and [`design/ADR.md`](design/ADR.md)
2. preserve the existing backend layering of routes, services, repositories, and providers
3. keep frontend API access under `frontend/src/api/`
4. do not silently diverge from accepted ADRs

If your change affects runtime behavior, storage boundaries, provider behavior, display rendering, or other accepted architectural decisions, add a new ADR under `design/adr/` instead of rewriting history away.

## License

SPF5000 is licensed under the [Apache License 2.0](LICENSE).
