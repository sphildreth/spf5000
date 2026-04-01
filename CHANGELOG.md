# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 1.1.0 - [Unreleased]

### Changed

- Updated SPF5000's documented DecentDB baseline to `v2.0.1+` for the latest features and improvements, while keeping the Pi installer on the default `DECENTDB_RELEASE_TAG=latest` behavior.
- Reduced backend RSS spikes on Linux/Pi deployments by trimming retained glibc heap after image-heavy ingest and background-color derivation work.
- Lowered DecentDB Python driver cache pressure on constrained devices by making the statement-cache size explicit and configurable in SPF5000.
- Reworked local-files scanning and import to stream directory traversal instead of materializing the full tree in memory, while keeping bounded sample results for the UI.
- Slimmed `/api/assets` list responses and the display playlist path so admin and display polling avoid hydrating heavyweight asset metadata and variant structures on every request.
- Reworked Google Photos sync to process remote items incrementally and merge per-source membership without holding the full selected library in memory.

## [1.0.0] - 2026-03-16

### Added

- FastAPI backend APIs for setup, authentication, health, status, settings, collections, assets, sources, import, and display playback.
- React + TypeScript + Vite frontend flows for `/setup`, `/login`, `/admin`, and the dedicated fullscreen `/display` route.
- Local-files provider support with recursive scanning, SHA-256 duplicate detection, managed originals, and generated display and thumbnail variants.
- Raspberry Pi appliance tooling via `scripts/install-pi.sh`, `scripts/doctor.sh`, and `scripts/uninstall-pi.sh`.
- App-managed quiet-hours behavior stored in DecentDB and enforced by the display client.

### Changed

- Established a repo-level semantic version source via the root `VERSION` file.
- Standardized backend and frontend project metadata on version `1.0.0`.

### Security

- Added single-admin bootstrap and session-cookie authentication for admin routes while keeping `/display` publicly accessible.

[Unreleased]: https://github.com/sphildreth/spf5000/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/sphildreth/spf5000/releases/tag/v1.0.0
