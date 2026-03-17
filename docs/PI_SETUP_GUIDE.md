# SPF5000 Raspberry Pi Setup Guide

This guide explains how to turn a Raspberry Pi running Raspberry Pi OS Desktop into an SPF5000 picture-frame appliance.

The operating-system prep is still manual, but the repetitive application wiring is now automated with:

- `scripts/install-pi.sh`
- `scripts/uninstall-pi.sh`
- `scripts/doctor.sh`

For installer-specific flags and managed file locations, see `docs/INSTALLER.md`.

## TLDR;

Do this:

```bash
sudo raspi-config
sudo raspi-config nonint do_blanking 1

# Use an existing Raspberry Pi desktop user, or create one with a home directory.
# If you pick a different username, replace "pi" consistently below.
sudo adduser pi

sudo mkdir -p /opt
cd /opt
sudo git clone https://github.com/sphildreth/spf5000.git
sudo chown -R pi:pi /opt/spf5000

cd /opt/spf5000
sudo ./scripts/install-pi.sh --user pi
sudo ./scripts/doctor.sh --user pi

sudo reboot
```

Then from another machine do this:

```text
http://<pi-hostname-or-ip>:8000/setup
```

## 1. Goal

The target end state is:

1. Raspberry Pi OS boots into the desktop automatically.
2. The chosen runtime user logs in automatically.
3. The SPF5000 backend starts as a `systemd` service.
4. Chromium launches automatically in kiosk mode.
5. Chromium opens the local `/display` route.
6. Administrators manage the frame from another device on the LAN.

This keeps the display appliance-like while preserving a normal web admin flow.

## 2. Recommended OS and hardware

Use:

- Raspberry Pi 3, Raspberry Pi 4, or Raspberry Pi 5
- Raspberry Pi OS with desktop (64-bit recommended)

Do not use Raspberry Pi OS Lite unless you are intentionally replacing the browser-kiosk runtime described in ADR 0007.

## 3. What the installer does and does not do

`scripts/install-pi.sh` automates:

- apt package installation for the Pi runtime
- backend virtualenv creation and dependency installation
- frontend production build creation
- runtime config generation
- `systemd` service installation
- Chromium autostart installation
- service enable/start

By default, the installer fetches the latest DecentDB release for both the Python binding source archive and the native release bundle. You can override that with `DECENTDB_RELEASE_TAG=vX.Y.Z` if you need to test or pin a different upstream DecentDB release.

The installer also detects whether the target OS exposes Chromium as `chromium` or `chromium-browser`, so the package name does not need to be adjusted manually between Debian and Raspberry Pi OS variants.

It does not try to reconfigure every Raspberry Pi OS desktop setting for you. These steps remain manual because they are OS-session specific and easier to verify explicitly:

- Desktop autologin
- screen blanking / power-management tweaks
- cloning or copying the SPF5000 repository onto the Pi

## 4. Prepare the Pi OS desktop session

The runtime user should be a normal desktop account with a home directory. SPF5000 installs the Chromium kiosk desktop entry into that user's `~/.config/autostart/` directory and also adds a managed command block to `~/.config/labwc/autostart` for Raspberry Pi OS Desktop's default `labwc` Wayland session. Raspberry Pi OS Desktop autologin should target that same user.

Enable desktop autologin:

```bash
sudo raspi-config
```

Then choose:

- `System Options`
- `Boot / Auto Login`
- `Desktop Autologin`

Disable the default Raspberry Pi OS screen blanking so SPF5000 can control quiet-hours behavior itself:

```bash
sudo raspi-config nonint do_blanking 1
```

You may also want the usual X11 anti-blanking settings in the runtime user's session:

```text
@xset s off
@xset -dpms
@xset s noblank
```

Cursor hiding is validated on both Raspberry Pi OS desktop backends now, but the mechanism differs by session type. The managed SPF5000 Chromium autostart entry delegates to a launcher script under `~/.config/autostart/`, and the installer also registers that same launcher in `~/.config/labwc/autostart` for `labwc` sessions. The launcher uses `unclutter-xfixes` on X11 sessions and requests native Chromium Wayland mode with `--ozone-platform-hint=auto` on the default `labwc` Wayland session so the display route's `cursor: none` styling is applied without Xwayland in the middle. It also logs each launch attempt to `/var/cache/spf5000/logs/spf5000-kiosk-launcher.log`.

You can verify the active desktop backend with:

```bash
sid="$(loginctl list-sessions --no-legend | awk '$3=="pi" {print $1; exit}')"
loginctl show-session "$sid" -p Type -p Desktop
```

Expected values:

- `Type=x11` means the kiosk launcher will use `unclutter-xfixes` for cursor hiding
- `Type=wayland` with `Desktop=rpd-labwc` means the kiosk launcher should request native Chromium Wayland mode

## 5. Put the repository on the Pi

The installer expects an existing SPF5000 checkout and, by default, assumes it lives at:

```text
/opt/spf5000
```

Typical setup:

```bash
sudo mkdir -p /opt
cd /opt
sudo git clone https://github.com/sphildreth/spf5000.git
sudo chown -R pi:pi /opt/spf5000
```

If you use a different checkout path, pass it with `--app-root`.

## 6. Let the installer fetch DecentDB

SPF5000 relies on the upstream DecentDB Python integration, which has two parts:

- the Python binding from `bindings/python`
- the native C API library from a DecentDB release bundle

`backend/requirements.txt` does not install either of those pieces for you.

On supported 64-bit Linux systems, `scripts/install-pi.sh` now downloads the latest DecentDB release plus the matching source archive automatically. No manual DecentDB clone is required for the supported Pi path unless you intentionally override `DECENTDB_RELEASE_TAG`.

On each run, `scripts/install-pi.sh` will:

1. resolve the matching DecentDB release for the current architecture
2. download and stage the native library under `/opt/spf5000/vendor/decentdb/`
3. download the matching DecentDB source archive and install the Python binding into `backend/.venv`
4. validate that the backend virtualenv can open a DecentDB connection
5. write `DECENTDB_NATIVE_LIB=/opt/spf5000/vendor/decentdb/libdecentdb.so` into the managed `systemd` unit

The supported prebuilt path is aimed at 64-bit Raspberry Pi OS on ARM64. If you are on an unsupported architecture, switch to a 64-bit Raspberry Pi OS image or handle DecentDB manually.

## 7. Run the installer

From the SPF5000 checkout:

```bash
cd /opt/spf5000
sudo ./scripts/install-pi.sh --user pi
```

The default Pi appliance paths are:

- app root: `/opt/spf5000`
- data dir: `/var/lib/spf5000`
- cache dir: `/var/cache/spf5000`
- config path: `/var/lib/spf5000/spf5000.toml`
- service name: `spf5000`
- host: `0.0.0.0`
- port: `8000`

The installer defaults the backend to `0.0.0.0` so the admin UI remains reachable from another device on the LAN. Chromium still opens the local `/display` route on the Pi itself.

Useful overrides:

```bash
sudo ./scripts/install-pi.sh \
  --user pi \
  --app-root /srv/spf5000 \
  --config-path /var/lib/spf5000/spf5000.toml \
  --host 127.0.0.1 \
  --port 8000
```

Use `--host 127.0.0.1` only if you intentionally want a loopback-only backend and do not need LAN admin access.

If you plan to use Google Photos on the frame, edit the generated `spf5000.toml` and fill in the `[providers.google_photos]` block with your Ambient API OAuth client ID and client secret before you start the connection flow from the admin UI.

## 8. Verify with doctor

After installation:

```bash
cd /opt/spf5000
sudo ./scripts/doctor.sh --user pi
```

The doctor checks:

- Linux / Raspberry Pi expectations
- service file presence
- service enabled/active state
- config file presence
- data/cache/log path presence
- path writeability for the runtime user
- local `/api/health` reachability
- frontend shell reachability on `/display`
- public bootstrap state from `/api/auth/session`
- public display playlist state, sleep-schedule state, and first-slide asset reachability
- Chromium binary and autostart entry presence for the active desktop backend, including labwc wiring, launcher logging, and live kiosk-process checks
- graphical-target and optional undervoltage hints

Warnings are acceptable for some manual Pi OS settings. Failing checks should be resolved before you treat the frame as ready.

## 9. First-run behavior

On a fresh install:

1. reboot the Pi
2. let the desktop auto-login complete
3. confirm Chromium opens `/display`
4. from another device on the LAN, browse to:

```text
http://<pi-hostname-or-ip>:8000/setup
```

5. create the single local admin account
6. sign in and import photos

The display route remains public and kiosk-oriented even while setup and admin auth happen elsewhere.

## 10. Runtime files installed by the appliance flow

The installer manages these key files and paths:

```text
/etc/systemd/system/spf5000.service
~/.config/autostart/spf5000-kiosk.desktop
/var/lib/spf5000/spf5000.toml
/var/lib/spf5000/
/var/cache/spf5000/
```

The repository itself remains in the chosen app root, and the backend still uses `backend/.venv` plus `frontend/dist` inside that checkout.

## 11. Updating an existing install

To update a Pi that is already running SPF5000, update the repository checkout and then re-run the installer.

`git pull` by itself is not the full update procedure. The installer also refreshes backend dependencies, reinstalls the DecentDB Python binding from the matching source archive, refreshes the staged DecentDB native library from the selected release, rebuilds `frontend/dist`, rewrites the managed `systemd` and kiosk autostart files, and restarts the backend service.

Typical update flow:

```bash
cd /opt/spf5000
git pull
sudo ./scripts/install-pi.sh --user pi
sudo ./scripts/doctor.sh --user pi
```

The runtime config at `/var/lib/spf5000/spf5000.toml` is preserved on re-run unless you explicitly use `--force`.

## 12. Sleep schedule behavior

SPF5000's quiet-hours behavior is controlled by application settings stored in DecentDB, not by the installer, `spf5000.toml`, `systemd`, cron, or Chromium flags.

The recommended model remains:

- keep the Pi powered on
- keep the backend running
- keep Chromium open
- configure the sleep schedule from the admin UI
- let the app use the frame's local device time to render a black screen and pause slideshow advancement during quiet hours
- let the display wake at the configured end time without shutting down the Pi or browser

That preserves the appliance feel without adding brittle reboot or monitor-power choreography.

## 13. Uninstalling the appliance wiring

To remove the `systemd` unit and Chromium autostart entry while keeping the runtime database, cache, and imported media:

```bash
sudo ./scripts/uninstall-pi.sh --user pi
```

To also remove the generated config plus the runtime data/cache paths:

```bash
sudo ./scripts/uninstall-pi.sh --user pi --purge
```

The uninstaller intentionally leaves the repository checkout alone.

## 14. Troubleshooting

### Doctor reports that the backend is loopback-only

That means the config is bound to `127.0.0.1` or `localhost`. Re-run the installer with `--host 0.0.0.0`, or edit the runtime config and restart the service.

### Doctor reports that DecentDB is missing

Re-run the installer first. On supported 64-bit systems it now downloads the matching DecentDB release bundle and matching source archive automatically.

The managed service uses `DECENTDB_NATIVE_LIB=/opt/spf5000/vendor/decentdb/libdecentdb.so` by default.

If the installer says no compatible DecentDB release asset is available for your architecture, move to a 64-bit Raspberry Pi OS image or handle DecentDB manually outside the supported appliance flow.

### Chromium opens before the backend is ready

The installed autostart entry already includes a short delay. If you still need more startup padding, edit the installed `.desktop` entry or rerun the installer after updating the template under `deploy/autostart/`.

### Chromium asks for "Choose password for new keyring"

That prompt comes from Chromium trying to use the desktop keyring. The managed kiosk launcher script should now launch Chromium with `--password-store=basic` so the prompt does not appear.

Re-run the installer to rewrite the autostart entry, then log out or reboot the Pi.

### The screen still blanks or powers down

Re-check:

- `raspi-config nonint do_blanking 1`
- your X11 session autostart entries for `xset`
- that the managed `~/.config/autostart/spf5000-kiosk.desktop` file still exists and has not been replaced by another desktop-session entry

### The mouse cursor is still visible

First confirm which desktop backend the Pi is actually running:

```bash
sid="$(loginctl list-sessions --no-legend | awk '$3=="pi" {print $1; exit}')"
loginctl show-session "$sid" -p Type -p Desktop
ps -ef | grep -E 'labwc|openbox|Xorg|Xwayland' | grep -v grep
```

Interpretation:

- `Type=wayland` and `labwc` mean the Pi is on Wayland; in that case the managed kiosk launcher script should include `--ozone-platform-hint=auto` so Chromium runs natively on Wayland
- `Type=x11` and `openbox`/`Xorg` mean the Pi is on X11; in that case the managed kiosk launcher script should launch `unclutter`

On Wayland, the managed kiosk launcher script should contain `--ozone-platform-hint=auto`. On X11, it should already launch `/usr/bin/unclutter --timeout 0.1 --jitter 8 --hide-on-touch --start-hidden --fork`.

Re-run the installer to refresh the managed autostart files, then log out or reboot the Pi. `doctor.sh` now warns if the installed launcher script is missing the Wayland selector for Wayland sessions or the X11 cursor-hiding command for X11 sessions.

### The admin UI is not reachable from another device

Confirm all of the following:

- the config host is not `127.0.0.1`
- the Pi has an IP address on the LAN
- `sudo systemctl status spf5000.service` is healthy
- `sudo ./scripts/doctor.sh --user pi` does not report service or health failures

## 15. Quick command summary

```bash
sudo raspi-config
sudo raspi-config nonint do_blanking 1

cd /opt/spf5000
git pull
sudo ./scripts/install-pi.sh --user pi
sudo ./scripts/doctor.sh --user pi

sudo systemctl status spf5000.service
sudo journalctl -u spf5000.service -f

sudo ./scripts/uninstall-pi.sh --user pi
```
