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
4. stops the managed backend service if it is already running
5. creates a timestamped pre-install database backup tarball when an existing DecentDB file is present
6. creates or refreshes `backend/.venv`
7. installs backend dependencies
8. downloads the matching DecentDB release bundle, installs the Python binding, and stages the native library
9. builds `frontend/dist`
10. creates a runtime `spf5000.toml` if needed
11. installs the `systemd` unit
12. installs the Chromium kiosk autostart entry, including automatic cursor hiding and a password-store setting that avoids desktop keyring prompts
13. enables and starts the backend service

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

The installer uses `DECENTDB_RELEASE_TAG=latest` by default. Set `DECENTDB_RELEASE_TAG=vX.Y.Z` in the environment if you want to override that latest-release behavior.

The runtime user should be a normal Raspberry Pi OS desktop account with a home directory. The installer writes the Chromium kiosk desktop entry to that user's `~/.config/autostart/` path and also adds a managed command block to `~/.config/labwc/autostart` so Raspberry Pi OS Desktop's default `labwc` Wayland session can launch the same kiosk script after login. Desktop Autologin should be configured for the same account.

If you run the installer while that desktop account is already logged in, the refreshed autostart files do not retroactively launch Chromium into the existing session. Log out or reboot once so the managed kiosk launcher runs in the next desktop login.

The managed Chromium autostart entry now delegates to a companion launcher script in the same autostart directory. That launcher script sets `--password-store=basic` so Chromium does not prompt for a GNOME keyring password in kiosk mode. On X11 sessions it also launches `unclutter-xfixes` through `/usr/bin/unclutter --timeout 0.1 --jitter 8 --hide-on-touch --start-hidden --fork`. On Raspberry Pi OS Desktop's default `labwc` Wayland session it instead requests native Chromium Wayland mode with `--ozone-platform-hint=auto`, so the display route's own `cursor: none` styling is not routed through Xwayland.

The installer defaults to `--host 0.0.0.0` so another device on the LAN can still reach `/setup`, `/login`, and `/admin`. Chromium still opens the local `http://127.0.0.1:8000/display` route when the host is the wildcard bind.

## Managed files and paths

By default the installer manages:

```text
/etc/systemd/system/spf5000.service
~/.config/autostart/spf5000-kiosk.desktop
~/.config/autostart/spf5000-kiosk-launch.sh
~/.config/labwc/autostart
/var/lib/spf5000/spf5000.toml
/var/lib/spf5000/
/var/cache/spf5000/
```

It also manages build/runtime artifacts inside the checkout:

```text
backend/.venv/
frontend/dist/
frontend/node_modules/
vendor/decentdb/
```

Use `deploy/systemd/spf5000.service.template`, `deploy/autostart/spf5000-kiosk.desktop.template`, and `deploy/config/spf5000.toml.example` as the source-of-truth templates.

When the installer finds an existing database, it also writes a timestamped backup archive under `installer-backups/` next to the active database file. The archive contains `spf5000.ddb` and includes `-wal` / `-shm` sidecars too when they exist so the preserved database state is more useful for recovery work.

## DecentDB requirement

The backend needs both parts of the upstream DecentDB Python integration:

- the Python binding from `bindings/python`
- the native C API library from the DecentDB release bundle

On supported 64-bit Linux architectures, the installer now downloads the configured DecentDB GitHub release plus the matching source archive. By default that is the latest upstream release. On each run it:

- extracts the native library into `vendor/decentdb/`
- installs or refreshes the Python binding into `backend/.venv`
- validates that `backend/.venv` can open a DecentDB connection
- writes `DECENTDB_NATIVE_LIB=<app-root>/vendor/decentdb/libdecentdb.so` into the managed `systemd` unit

The supported prebuilt path is intended for 64-bit Raspberry Pi OS on ARM64. If no compatible DecentDB release asset is available for the current architecture, the installer exits with a clear error instead of silently enabling the backend in degraded `NullConnection` mode.

## Re-running the installer

`install-pi.sh` is designed to be mostly idempotent:

- apt installs can be repeated
- an existing database is preserved into a timestamped `installer-backups/spf5000-ddb-install-backup-<timestamp>.tar.gz` archive before install changes are applied
- the virtualenv can be refreshed
- the DecentDB binding and native library are refreshed from the selected release each run
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
- frontend shell reachability on `/display`
- bootstrap state from `/api/auth/session`
- public display playlist state, active sleep-schedule hints, and first-slide asset reachability
- Chromium availability, XDG/labwc kiosk autostart wiring, launcher logging, log freshness since boot, and a live Chromium process check for the active desktop session
- graphical-target and optional undervoltage hints

Warnings indicate manual Pi OS tuning or non-blocking issues. Failing checks mean the appliance setup is not ready.

If the backend is healthy but the Pi-connected monitor stays black, `doctor.sh` now also tells you whether the display is intentionally black because quiet hours are active, whether the playlist is empty, whether the first display asset responds locally, and whether the managed launcher log at `/var/cache/spf5000/logs/spf5000-kiosk-launcher.log` has been updated since boot.

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
- the active desktop backend is the one you intend to run, and the managed kiosk autostart file has been refreshed for it
- any desired X11 anti-blanking settings are present if you are using an X11 session
- the Pi has stable LAN connectivity

That keeps the installer boring, readable, and resilient across Raspberry Pi OS desktop-session variations.
