# SPF5000 Follow-On Implementation Prompt
## Pi Appliance Installer + Uninstall + Doctor Scripts

You are working in the existing `spf5000` repository after the current in-flight work completes.

Your task is to implement a **first-pass Raspberry Pi appliance installation toolchain** for SPF5000.

The goal is to automate the repetitive operational steps needed to turn a Raspberry Pi running Raspberry Pi OS Desktop into a hands-off SPF5000 picture frame appliance.

This is intentionally **Pi-specific** and **opinionated**. Do not attempt to create a universal Linux installer.

---

## Goals

Implement the following:

1. `scripts/install-pi.sh`
2. `scripts/uninstall-pi.sh`
3. `scripts/doctor.sh`
4. supporting templates/files for:
   - systemd service
   - Chromium autostart
   - example `spf5000.toml`
5. documentation updates
6. ADR/design updates as appropriate

The scripts should support the current architecture:

- FastAPI backend
- React + TypeScript + Vite frontend
- DecentDB for app data/settings
- Raspberry Pi OS Desktop
- Chromium kiosk display at `/display`
- admin UI on LAN
- slideshow sleep schedule handled by the app

---

## Scope

This work is for:

- Raspberry Pi 3 / Raspberry Pi 4
- Raspberry Pi OS with desktop
- local browser kiosk runtime
- local backend service
- a normal non-root runtime user

Do **not** attempt to support:
- arbitrary distros
- Docker deployment
- PAM auth
- system-wide login rework beyond what is reasonable to document/check
- complex package manager abstraction
- multi-device orchestration

Keep it practical and appliance-focused.

---

## High-Level Requirements

### install-pi.sh
The installer should automate most of the setup documented in the Pi setup guide.

It should:
- validate it is running on a Raspberry Pi / Debian-like environment as reasonably as practical
- check for root/sudo context where needed
- accept a small set of parameters
- install required apt packages
- create needed directories
- set ownership/permissions
- create or update a Python virtualenv
- install backend dependencies
- install/copy config template if missing
- install systemd service file
- install Chromium autostart entry for the selected user
- enable/start the SPF5000 backend service
- print clear next steps / status summary

It should be safe to run more than once where practical.

### uninstall-pi.sh
The uninstaller should remove the operational appliance setup without trying to destroy the user’s data unless explicitly requested.

It should:
- stop/disable the systemd service
- remove the service file
- remove the Chromium autostart entry
- optionally remove generated config/templates
- preserve database/cache/data by default
- support an explicit destructive flag if you choose to add one

### doctor.sh
The doctor script should check the health/readiness of the Pi appliance setup.

It should verify things like:
- required binaries installed
- config file exists
- service file exists
- service enabled/running
- configured paths exist and are writable
- backend health endpoint responds if the service is running
- Chromium autostart file exists
- likely misconfigurations are surfaced clearly

The doctor script should be easy to run and easy to read.

---

## Script Philosophy

These scripts must be:

- readable
- transparent
- opinionated
- mostly idempotent
- conservative with destructive actions
- verbose enough to be helpful
- not magic

Do **not** build a giant installer framework.
Do **not** introduce fancy bash metaprogramming.
Do **not** make them depend on obscure shell features unnecessarily.

Readable bash is preferred.

Use:
- `set -euo pipefail`
- clear logging helpers
- defensive checks
- comments where useful

---

## Expected Inputs / Defaults

The installer should support sane defaults and allow overrides.

Suggested defaults:

- app root: `/opt/spf5000`
- data dir: `/var/lib/spf5000`
- cache dir: `/var/cache/spf5000`
- config path: `/var/lib/spf5000/spf5000.toml`
- service name: `spf5000`
- backend bind host: `127.0.0.1`
- backend bind port: `8000`

Suggested runtime user:
- explicit `--user <username>` argument
- do not silently assume the current shell user unless documented and intentional

Suggested CLI options:
- `--user`
- `--app-root`
- `--data-dir`
- `--cache-dir`
- `--config-path`
- `--host`
- `--port`
- `--skip-apt`
- `--force`

Keep the option surface modest.

---

## Required Repository Additions

Add a directory structure like:

```text
scripts/
  install-pi.sh
  uninstall-pi.sh
  doctor.sh

deploy/
  systemd/
    spf5000.service.template
  autostart/
    spf5000-kiosk.desktop.template
  config/
    spf5000.toml.example
```

If the repo already has a slightly different structure, integrate cleanly with what exists.

---

## Detailed Requirements

## 1. install-pi.sh

The installer should perform the following logical steps.

### A. Preflight
- verify OS is compatible enough
- verify required arguments or defaults
- verify target user exists
- verify `systemctl` is available
- verify apt is available unless `--skip-apt`
- print an install summary before making changes if helpful

### B. Install packages
Install the required packages for the Pi appliance runtime, such as:
- Chromium
- Python venv/pip support
- any small helper packages the project needs
- optionally `unclutter`

Package names may vary by Pi OS version. Handle obvious Chromium package-name differences pragmatically if needed.

### C. Create directories
Ensure directories exist:
- app root
- data dir
- cache dir
- any log/runtime dirs the project expects

Apply ownership to the runtime user.

### D. Python environment
- create `.venv` if missing
- update pip
- install backend requirements
- optionally install frontend/build dependencies only if the repo’s workflow requires it

Do not invent a build pipeline if the repo already defines one.

### E. Runtime config
If config file does not exist, create it from template/example.
Do not overwrite an existing config unless explicitly requested.

Populate the config with the selected paths/host/port.

### F. systemd service
Install the service file from template.
Substitute:
- runtime user
- working directory
- config path
- backend host/port if needed

Then:
- `systemctl daemon-reload`
- `systemctl enable`
- `systemctl restart` or `start`

### G. Chromium autostart
Install the desktop autostart entry under the selected user’s home directory, for example:

```text
~/.config/autostart/spf5000-kiosk.desktop
```

It should launch Chromium to:

```text
http://127.0.0.1:8000/display
```

using kiosk-friendly flags.

Support a short startup delay in the autostart command if appropriate.

### H. Final output
Print a clear summary including:
- where config lives
- service name
- how to check status
- how to open admin UI from another device
- what still may need to be configured manually
- note that slideshow sleep schedule is controlled by the app, not the installer

---

## 2. uninstall-pi.sh

The uninstaller should:
- confirm what it is going to remove
- stop the service if present
- disable the service if present
- remove the service file
- reload systemd
- remove the user autostart `.desktop` file
- optionally remove generated config/templates if they were installer-managed
- preserve user data by default

Support an optional explicit flag for removing data/config if you want, but make preservation the default behavior.

Do not remove arbitrary repo content by surprise.

---

## 3. doctor.sh

The doctor script should emit a clear pass/fail/warn style report.

Check at least:
- running on Linux
- service file exists
- service enabled
- service active
- config file exists
- data dir exists
- cache dir exists
- directories writable by runtime user
- backend health endpoint reachable
- Chromium binary available
- autostart desktop entry exists
- likely boot target assumptions documented if not directly testable

Nice-to-have checks:
- detect undervoltage warning history if easily and safely available
- verify hostname/IP and print admin URL hint
- warn if no admin user is bootstrapped yet

Do not make the doctor script noisy or fragile.

---

## 4. systemd service template

Create a service template suitable for the current backend structure.

Requirements:
- run as the selected non-root user
- restart automatically on failure
- use the configured app/config paths
- bind backend to localhost by default unless overridden
- be easy for a human to inspect

---

## 5. Chromium autostart template

Create a `.desktop` template for kiosk startup.

Requirements:
- fullscreen/kiosk mode
- no browser chrome
- no error dialogs
- no first-run prompts
- local `/display` URL
- optional startup delay wrapper if needed

Keep it simple.

---

## 6. Example spf5000.toml

Create a documented example config that matches the current runtime design.

It should clearly distinguish runtime config from app settings stored in DecentDB.

---

## 7. Documentation updates

Update user-facing documentation under `docs/` and relevant internal architecture docs under `design/`.

At minimum update or add:
- `docs/PI_SETUP_GUIDE.md`
- `README.md`

If appropriate, add:
- `docs/INSTALLER.md`
- `docs/TROUBLESHOOTING.md`

Document:
- how to run the installer
- how to uninstall
- how to run doctor
- what is automated vs still manual
- how the Pi appliance boot flow works
- where files are installed
- where config lives

Also update relevant ADRs or add a new ADR for:
- using installer scripts to provision Pi appliance runtime
- keeping installer scope Pi-specific and intentionally opinionated

---

## 8. Constraints / Non-Goals

Do not:
- overengineer the installer
- build a package manager abstraction layer
- implement a giant TUI wizard
- auto-modify every conceivable Pi OS desktop setting if it becomes fragile
- attempt to manage all future deployment types

It is okay if a couple of steps remain documented/manual, especially if they are OS-version-sensitive.
But automate the high-value repetitive steps.

---

## 9. Acceptance Criteria

This work is complete when:

- `scripts/install-pi.sh` exists and is readable
- installer can provision a Pi appliance setup on Raspberry Pi OS Desktop
- service is installed and starts successfully
- Chromium autostart entry is installed for the selected user
- config file is created if missing
- installer is reasonably safe to re-run
- `scripts/uninstall-pi.sh` exists and removes the operational setup without deleting user data by default
- `scripts/doctor.sh` exists and provides useful health checks
- templates/examples are present
- documentation is updated
- ADR/design docs reflect the installer strategy

---

## 10. Implementation Notes

Prefer a first-pass implementation that is:
- practical
- explicit
- easy to review
- easy to improve later

This is an appliance project.
The installer should feel like a boring, competent operator wrote it.

The goal is to reduce manual setup burden and make the Pi deployment repeatable, not to create a full-blown installation platform.
