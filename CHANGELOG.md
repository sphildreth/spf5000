# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Updated SPF5000's documented DecentDB baseline to `v1.7.4+` for the upstream core-engine memory-leak fixes, while keeping the Pi installer on the default `DECENTDB_RELEASE_TAG=latest` behavior.

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
