# SPF5000 Pi Installer

SPF5000 includes a first-pass Raspberry Pi appliance installer toolchain for Raspberry Pi OS Desktop:

- `scripts/install-pi.sh`
- `scripts/uninstall-pi.sh`
- `scripts/doctor.sh`

These scripts are intentionally Pi-specific and opinionated. They automate the supported browser-kiosk appliance flow instead of trying to be a generic Linux installer.

## What `install-pi.sh` does

`install-pi.sh` expects an existing SPF5000 checkout and then:

1. validates the target environment
2. installs required apt packages unless `--skip-apt` is used
3. creates the runtime directories
4. creates or refreshes `backend/.venv`
5. installs backend dependencies
6. validates or installs the DecentDB Python binding from a nearby checkout
7. builds `frontend/dist`
8. creates a runtime `spf5000.toml` if needed
9. installs the `systemd` unit
10. installs the Chromium kiosk autostart entry
11. enables and starts the backend service

When installing Chromium, the script automatically chooses the distro-supported package name (`chromium` or `chromium-browser`) based on the apt candidate available on the target system.

## Install command

Typical install:

```bash
cd /opt/spf5000
sudo ./scripts/install-pi.sh --user pi
```

Common options:

- `--user <username>` - required runtime user
- `--app-root <path>` - SPF5000 checkout path
- `--data-dir <path>` - runtime data directory
- `--cache-dir <path>` - runtime cache/log directory root
- `--config-path <path>` - runtime config path
- `--host <host>` - backend bind host
- `--port <port>` - backend bind port
- `--skip-apt` - skip apt installation and validate only
- `--force` - overwrite an existing generated config and bypass the non-Pi hardware guard

The runtime user should be a normal Raspberry Pi OS desktop account with a home directory. The installer writes the Chromium kiosk autostart entry to that user's `~/.config/autostart/` path, and Desktop Autologin should be configured for the same account.

The installer defaults to `--host 0.0.0.0` so another device on the LAN can still reach `/setup`, `/login`, and `/admin`. Chromium still opens the local `http://127.0.0.1:8000/display` route when the host is the wildcard bind.

## Managed files and paths

By default the installer manages:

```text
/etc/systemd/system/spf5000.service
~/.config/autostart/spf5000-kiosk.desktop
/var/lib/spf5000/spf5000.toml
/var/lib/spf5000/
/var/cache/spf5000/
```

It also manages build/runtime artifacts inside the checkout:

```text
backend/.venv/
frontend/dist/
frontend/node_modules/
```

Use `deploy/systemd/spf5000.service.template`, `deploy/autostart/spf5000-kiosk.desktop.template`, and `deploy/config/spf5000.toml.example` as the source-of-truth templates.

## DecentDB requirement

The backend still needs the real DecentDB Python binding. The installer will succeed only if one of these is true:

- `backend/.venv` can already import `decentdb`
- a nearby checkout such as `../decentdb/bindings/python` exists and can be installed into `backend/.venv`

If not, the installer exits with a clear error instead of silently enabling the backend in degraded `NullConnection` mode.

## Re-running the installer

`install-pi.sh` is designed to be mostly idempotent:

- apt installs can be repeated
- the virtualenv can be refreshed
- the service and autostart files are rewritten each run
- the config file is preserved unless `--force` is used

This makes it reasonable to rerun the installer after updating the repository checkout.

## Using `doctor.sh`

Run:

```bash
cd /opt/spf5000
sudo ./scripts/doctor.sh --user pi
```

`doctor.sh` prints a pass/warn/fail report for:

- Linux / Raspberry Pi assumptions
- `systemd` service file presence
- service enabled/active state
- runtime config presence
- data/cache/log path presence
- writeability for the runtime user
- local health endpoint reachability
- bootstrap state from `/api/auth/session`
- Chromium availability and kiosk autostart wiring
- graphical-target and optional undervoltage hints

Warnings indicate manual Pi OS tuning or non-blocking issues. Failing checks mean the appliance setup is not ready.

## Using `uninstall-pi.sh`

To remove only the appliance wiring:

```bash
sudo ./scripts/uninstall-pi.sh --user pi
```

That removes:

- the `spf5000.service` unit
- the Chromium autostart entry

It preserves:

- the runtime config
- the database
- imported files
- cache and logs
- the repository checkout

To also remove the generated config plus data/cache directories:

```bash
sudo ./scripts/uninstall-pi.sh --user pi --purge
```

## Manual Pi OS steps that remain outside the installer

The installer deliberately does not try to own every desktop-session knob. You should still verify:

- the runtime user is a normal desktop account with a home directory
- Desktop Autologin is enabled in `raspi-config`
- screen blanking is disabled
- any desired X11 anti-blanking settings are present
- the Pi has stable LAN connectivity

That keeps the installer boring, readable, and resilient across Raspberry Pi OS desktop-session variations.
