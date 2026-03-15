# ADR 0010: Use Pi-Specific Appliance Installer Toolchain

- Status: Accepted
- Date: 2026-03-15

## Context
ADR 0007 commits SPF5000 to a Raspberry Pi browser-kiosk runtime, and ADR 0009 commits runtime config, bootstrap flow, and local admin auth to a small appliance model. Turning that accepted architecture into a repeatable deployed device still requires operational setup on Raspberry Pi OS Desktop: package installation, runtime directories, `spf5000.toml`, a backend `systemd` unit, Chromium autostart, health checks, and operator documentation. A generic cross-distro installer would add portability work, abstraction, and testing surface that do not help the V1 Pi appliance target.

## Decision
Use a Pi-specific, opinionated installer toolchain for the browser-kiosk appliance runtime rather than a generic Linux installer. Center the deployment automation on readable Bash scripts (`scripts/install-pi.sh`, `scripts/uninstall-pi.sh`, and `scripts/doctor.sh`), deployment templates under `deploy/systemd/`, `deploy/autostart/`, and `deploy/config/`, and matching docs updates. This toolchain automates deployment around the existing FastAPI, React, DecentDB, `spf5000.toml`, and Chromium `/display` architecture without changing the accepted runtime or auth boundaries.

## Consequences
- Installation, recovery, and field servicing become more repeatable for the actual Raspberry Pi appliance target.
- The operational path stays understandable because it encodes one supported deployment model instead of a distro abstraction layer.
- SPF5000 remains intentionally opinionated about Raspberry Pi OS Desktop, `systemd`, and Chromium kiosk assumptions.
- Operators who want other distros or packaging models will need separate documentation or future ADR-backed work instead of expecting this installer to be portable.
