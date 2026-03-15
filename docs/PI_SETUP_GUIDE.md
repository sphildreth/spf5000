# SPF5000 Raspberry Pi Setup Guide

This guide explains how to configure a Raspberry Pi so **SPF5000** behaves like a real picture frame appliance:

- power on
- boot automatically
- log in automatically
- start the SPF5000 backend automatically
- launch the fullscreen display automatically
- show pictures without user interaction
- sleep on a schedule such as **22:00 to 08:00**

This document is written as a user-facing setup guide intended for the repository `docs/` directory.

---

## 1. Goal

The target behavior is:

1. The Raspberry Pi powers on.
2. Raspberry Pi OS boots into the desktop automatically.
3. The Pi logs in automatically as the configured frame user.
4. The SPF5000 backend starts as a system service.
5. Chromium launches automatically in fullscreen kiosk mode.
6. Chromium opens the local SPF5000 display page.
7. The display begins showing images automatically.
8. During configured quiet hours such as **22:00 to 08:00**, the display goes black and stops slideshow movement.
9. In the morning, the slideshow resumes automatically.

The end result should be that someone can turn it on, walk away, and a few minutes later see pictures moving across the screen.

---

## 2. Recommended OS Choice

Use:

- **Raspberry Pi OS with desktop**

Do **not** use Raspberry Pi OS Lite for the appliance runtime unless you plan to replace the browser-based display architecture.

Why desktop is recommended:

- SPF5000 display runs in a browser
- kiosk mode works best in a graphical session
- auto-login into desktop is straightforward
- Chromium is easy to launch and manage
- this matches the intended full-screen display architecture

---

## 3. Assumptions

This guide assumes:

- the Raspberry Pi is already installed and booting
- the Pi is connected to the monitor
- SSH is available
- the project will run locally on the Pi
- the SPF5000 backend serves the display at:

```text
http://127.0.0.1:8000/display
```

Adjust paths and usernames as needed for your environment.

---

## 4. Suggested Runtime User

Use a normal non-root user account for the frame runtime, for example:

- `steven`
- `pi`
- `spf5000`

Examples in this guide use:

```text
steven
```

The browser kiosk session and the application files should run under this normal user account, not root.

---

## 5. Install Required Packages

Update the Pi and install the basic dependencies.

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y chromium-browser python3-venv python3-pip
```

Depending on Raspberry Pi OS version, the Chromium package name may differ. If `chromium-browser` is not available, use:

```bash
sudo apt install -y chromium
```

Optional helpful tools:

```bash
sudo apt install -y unclutter xdotool
```

`unclutter` is useful for hiding the mouse cursor when idle.

---

## 6. Set Raspberry Pi OS to Boot to Desktop with Auto-Login

Run:

```bash
sudo raspi-config
```

Go to:

- **System Options**
- **Boot / Auto Login**
- choose **Desktop Autologin**

This ensures the Pi:
- boots to the graphical desktop
- automatically logs in the configured user
- launches the kiosk environment without manual interaction

Reboot afterward if prompted.

---

## 7. Disable OS-Level Screen Blanking

SPF5000 should control the visual state of the display. The operating system should **not** randomly blank the screen.

Use:

```bash
sudo raspi-config nonint do_blanking 1
```

Then reboot:

```bash
sudo reboot
```

This disables default Raspberry Pi OS screen blanking behavior.

### Additional X/Chromium-friendly anti-blanking settings

It is also useful to disable screen saver and energy-management behavior in the graphical session.

Create this directory if it does not exist:

```bash
mkdir -p ~/.config/lxsession/LXDE-pi
```

Create or edit:

```bash
nano ~/.config/lxsession/LXDE-pi/autostart
```

Add:

```text
@xset s off
@xset -dpms
@xset s noblank
@unclutter -idle 0.5 -root
```

These settings:
- disable X screen saver
- disable DPMS power management
- prevent blanking
- hide the mouse cursor

Note: if your Pi OS desktop session differs slightly, the autostart location may vary. The intent remains the same.

---

## 8. Install SPF5000 on the Pi

The exact install flow depends on how the repository is deployed, but a simple structure is:

```text
/opt/spf5000
/var/lib/spf5000
/var/cache/spf5000
```

Example:

```bash
sudo mkdir -p /opt/spf5000
sudo mkdir -p /var/lib/spf5000
sudo mkdir -p /var/cache/spf5000
sudo chown -R steven:steven /opt/spf5000 /var/lib/spf5000 /var/cache/spf5000
```

Clone the repo:

```bash
cd /opt
git clone https://github.com/sphildreth/spf5000.git
sudo chown -R steven:steven /opt/spf5000
```

Create a virtual environment:

```bash
cd /opt/spf5000
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

Install backend dependencies:

```bash
pip install -r backend/requirements.txt
```

If your frontend is prebuilt, copy/build the frontend assets according to the repository instructions.

---

## 9. Create `spf5000.toml`

Create a runtime config file. For example:

```bash
mkdir -p /var/lib/spf5000
nano /var/lib/spf5000/spf5000.toml
```

Example config:

```toml
[server]
host = "127.0.0.1"
port = 8000

[paths]
data_dir = "/var/lib/spf5000"
cache_dir = "/var/cache/spf5000"
database_path = "/var/lib/spf5000/spf5000.ddb"

[logging]
level = "INFO"
```

This file should contain only runtime/startup concerns, not general slideshow or admin settings.

---

## 10. Create the SPF5000 systemd Service

Create the service file:

```bash
sudo nano /etc/systemd/system/spf5000.service
```

Example:

```ini
[Unit]
Description=SPF5000 backend
After=network-online.target
Wants=network-online.target

[Service]
User=steven
Group=steven
WorkingDirectory=/opt/spf5000/backend
Environment=SPF5000_CONFIG=/var/lib/spf5000/spf5000.toml
ExecStart=/opt/spf5000/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Adjust:
- username
- working directory
- uvicorn module path
- config path

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable spf5000.service
sudo systemctl start spf5000.service
```

Check status:

```bash
systemctl status spf5000.service
```

Check logs:

```bash
journalctl -u spf5000.service -f
```

The backend must be working before the browser can render the slideshow.

---

## 11. Configure Chromium Kiosk Auto-Start

The browser should be launched by the desktop session after auto-login.

Create the autostart directory:

```bash
mkdir -p ~/.config/autostart
```

Create the desktop entry:

```bash
nano ~/.config/autostart/spf5000-kiosk.desktop
```

Add:

```ini
[Desktop Entry]
Type=Application
Name=SPF5000 Kiosk
Exec=chromium --kiosk --noerrdialogs --disable-infobars --no-first-run --start-maximized --incognito http://127.0.0.1:8000/display
X-GNOME-Autostart-enabled=true
```

This launches Chromium:
- fullscreen
- without normal browser chrome
- directly to the SPF5000 display page

### Optional delayed launch

If Chromium starts before the backend is ready, use a short delay:

```ini
[Desktop Entry]
Type=Application
Name=SPF5000 Kiosk
Exec=sh -c "sleep 8; chromium --kiosk --noerrdialogs --disable-infobars --no-first-run --start-maximized --incognito http://127.0.0.1:8000/display"
X-GNOME-Autostart-enabled=true
```

This is often a practical improvement on slower Pi boot sequences.

---

## 12. First-Run Behavior

Once the system is configured:

1. Reboot the Pi.
2. The desktop should auto-login.
3. The SPF5000 backend should start.
4. Chromium should launch automatically.
5. The display should open to the slideshow route.

If no admin account exists yet, the admin bootstrap flow should still work from another device on the LAN by browsing to:

```text
http://<pi-ip>:8000/setup
```

The display itself should remain dedicated to slideshow behavior.

---

## 13. Recommended Sleep Schedule Behavior

For the nightly quiet period, such as:

- **22:00 to 08:00**

the recommended design is:

- do **not** power off the Pi
- do **not** stop Chromium
- do **not** shut down the backend

Instead, SPF5000 should:
- stop slideshow advancement
- render a black full-screen display
- resume the slideshow automatically at the configured wake time

### Why this is recommended

This approach is simpler and more reliable because:
- the browser remains open
- the backend remains running
- the system wakes instantly at the scheduled time
- there is no complex reboot or power-control dependency

The application, not the OS, should control the visual sleep schedule.

---

## 14. How the Fullscreen Display Should Behave

The intended display architecture is:

- Chromium opens `http://127.0.0.1:8000/display`
- the display route renders the slideshow fullscreen
- there is no visible admin UI on the frame
- the slideshow uses a dual-layer image renderer
- the next image is preloaded before transition
- transitions should not reveal a full black screen between images

For the preferred transition style:
- the next image slides in left-to-right
- the current image remains visible until the next image is ready
- there is no flicker or blank frame between images

This behavior is implemented by SPF5000 itself, not by Chromium.

---

## 15. Recommended Network Model

SPF5000 should be usable like this:

- the frame display is local on the Pi monitor
- admin access happens from another device on the LAN
- the admin UI is reachable at:

```text
http://<pi-ip>:8000/admin
```

This keeps the frame appliance-like while still making it easy to manage.

---

## 16. Suggested NAS Mount Strategy

If images are stored on a NAS, mount the share on the Pi and let SPF5000 read from a stable local mount path.

Example mount point:

```text
/mnt/photos
```

Recommended approach:
- mount the NAS at boot
- let SPF5000 scan or sync from the mounted path
- optionally keep a local fallback image cache in case the NAS is unavailable

SPF5000 should continue showing cached images if the network share goes offline.

---

## 17. Testing Checklist

After setup, verify these manually:

### Boot and startup
- Pi boots without user input
- desktop logs in automatically
- Chromium launches automatically
- the display page appears fullscreen

### Backend
- SPF5000 service starts automatically
- backend restarts if manually stopped
- admin UI is reachable from another device

### Display behavior
- slideshow starts automatically
- transitions are smooth
- no black flash appears between images
- the mouse cursor is hidden
- the screen does not blank by itself

### Sleep schedule
- display goes black during configured quiet hours
- slideshow resumes automatically after quiet hours end

### Recovery
- after unplug/replug, the system returns to slideshow mode without manual work
- if the backend is briefly unavailable, the browser recovers cleanly
- cached images continue displaying if remote sources are unavailable

---

## 18. Troubleshooting

### Chromium opens before the backend is ready
Use a delayed autostart command with `sleep 8` or similar.

### Screen goes blank after some time
Re-check:
- `raspi-config` screen blanking setting
- X session autostart entries:
  - `@xset s off`
  - `@xset -dpms`
  - `@xset s noblank`

### Mouse pointer is visible
Install and enable `unclutter`.

### Browser crashes or closes
The desktop session should relaunch Chromium at next reboot, but you may later want a watchdog or wrapper script if needed.

### Backend is not reachable
Check:

```bash
systemctl status spf5000.service
journalctl -u spf5000.service -f
```

### Undervoltage warnings
Use a proper Raspberry Pi power supply or a known-good 5V source and quality cable. Portable monitors should ideally be powered separately from the Pi.

---

## 19. Example End-State Summary

A successful final setup looks like this:

- Raspberry Pi OS with desktop
- desktop auto-login enabled
- screen blanking disabled
- SPF5000 backend runs as a systemd service
- Chromium launches automatically in kiosk mode
- display route runs fullscreen
- admin UI is available from other LAN devices
- the slideshow runs all day
- the display goes black from 22:00 to 08:00
- in the morning the slideshow resumes automatically

That is the intended “turn it on and walk away” experience.

---

## 20. Future Improvements

Possible future enhancements include:
- wrapper script to wait for backend health before launching Chromium
- health-check watchdog for browser process
- automatic restart of Chromium if it exits unexpectedly
- optional monitor power management integration
- optional hostname-based local URL such as `http://pictures.local:8000/admin`
- optional installer script to automate most of the steps in this guide

---

## 21. Quick Command Summary

```bash
sudo raspi-config
sudo raspi-config nonint do_blanking 1

sudo apt update
sudo apt upgrade -y
sudo apt install -y chromium-browser python3-venv python3-pip unclutter

mkdir -p ~/.config/autostart
nano ~/.config/autostart/spf5000-kiosk.desktop

sudo nano /etc/systemd/system/spf5000.service
sudo systemctl daemon-reload
sudo systemctl enable spf5000.service
sudo systemctl start spf5000.service

systemctl status spf5000.service
journalctl -u spf5000.service -f
```

---

## 22. Notes for Repository Placement

This file is intended to live under:

```text
docs/PI_SETUP_GUIDE.md
```

It complements:
- product/design docs under `design/`
- user-facing operational documentation under `docs/`

