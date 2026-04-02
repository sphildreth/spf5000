# PhotoSync + Raspberry Pi 4 + SPF5000 Setup Guide

This guide walks you through setting up **automatic photo transfer** from an Android phone to your SPF5000-powered digital picture frame running on a Raspberry Pi 4.

## Overview

**PhotoSync** is an Android/iOS app that transfers photos from your phone to a destination of your choice. We'll configure it to automatically send photos to your Raspberry Pi, where SPF5000 will pick them up and display them.

### Why This Works

- **No cloud dependency** — Photos transfer directly over your home WiFi
- **Automatic** — Once configured, photos transfer without user intervention
- **Wife-friendly** — She just takes photos; everything else happens automatically
- **Reliable** — PhotoSync has been around for 10+ years and just works
- **No Google API restrictions** — Unlike Google Photos integration, this uses standard file sharing

---

## Prerequisites

### Hardware

- Raspberry Pi 4 (any model with Ethernet or WiFi)
- Android phone (your wife's phone)
- Both devices on the same home WiFi network

### Software

- SPF5000 installed and running on the Pi (see `docs/PI_SETUP_GUIDE.md`)
- PhotoSync app on Android phone (available on Play Store or F-Droid)

### Information You'll Need

- Your Pi's hostname or IP address (e.g., `pictures` or `192.168.1.50`)
- Your Pi's username (e.g., `pi` or your actual username)
- Your Pi's password

---

## Part 1: Prepare the Raspberry Pi

### Step 1.1: Verify SPF5000 Import Directory

SPF5000 watches a specific directory for new photos. By default, this is:

```
/var/lib/spf5000/sources/local-files/import/
```

Verify this directory exists:

```bash
ls -la /var/lib/spf5000/sources/local-files/import/
```

If you get an error, create it:

```bash
sudo mkdir -p /var/lib/spf5000/sources/local-files/import/
sudo chown -R $USER:$USER /var/lib/spf5000/sources/local-files/import/
```

### Step 1.2: Enable SMB/CIFS Sharing on the Pi

PhotoSync transfers files over SMB (Windows file sharing). We need to set this up on the Pi.

**Install Samba:**

```bash
sudo apt update
sudo apt install samba samba-common-bin -y
```

**Create a Samba password for your user:**

```bash
sudo smbpasswd -a $USER
```

Enter a password when prompted. **Write this down** — you'll need it in PhotoSync.

**Create the Samba configuration:**

```bash
sudo nano /etc/samba/smb.conf
```

Add this to the **end** of the file:

```ini
[spf5000-import]
    path = /var/lib/spf5000/sources/local-files/import
    browseable = yes
    read only = no
    create mask = 0644
    directory mask = 0755
    force user = pi
    valid users = pi
```

**Important:** Replace `pi` with your actual username if different.

**Save and exit:** Press `Ctrl+X`, then `Y`, then `Enter`.

**Restart Samba:**

```bash
sudo systemctl restart smbd
sudo systemctl enable smbd
```

**Verify Samba is running:**

```bash
sudo systemctl status smbd
```

You should see `active (running)` in green.

### Step 1.3: Note Your Pi's Network Information

**Find your Pi's IP address:**

```bash
hostname -I
```

Write down the first IP address (e.g., `192.168.1.50`).

**Find your Pi's hostname:**

```bash
hostname
```

Write this down too (e.g., `pictures`).

---

## Part 2: Configure PhotoSync on Android

### Step 2.1: Install PhotoSync

**From Google Play Store:**

1. Open Play Store on the Android phone
2. Search for "PhotoSync"
3. Install "PhotoSync - wireless photo transfer" by touchbyte GmbH
4. Open the app

**Alternative: From F-Droid (free version):**

1. Install F-Droid from https://f-droid.org
2. Open F-Droid and search for "PhotoSync"
3. Install and open

**Note:** The Play Store version has a free trial, then costs ~$3-5 one-time. The F-Droid version is free but may have fewer features. For automatic transfers, the paid version is worth it.

### Step 2.2: Grant Permissions

When you first open PhotoSync:

1. **Grant photo/media access** — Tap "Allow" when prompted
2. **Grant location access** (optional) — This helps with automatic transfer triggers
3. **Grant notification access** — So you can see transfer status

### Step 2.3: Configure the Companion (Pi)

1. In PhotoSync, tap the **gear icon** (Settings) in the top right
2. Scroll down and tap **"Configure companion"**
3. Tap **"Create new companion"**
4. Select **"Windows/SMB"** as the type

**Fill in the connection details:**

| Field | Value |
|-------|-------|
| **Name** | `SPF5000 Frame` (or whatever you want to call it) |
| **Host/IP** | Your Pi's IP address (e.g., `192.168.1.50`) or hostname (e.g., `pictures`) |
| **Share** | `spf5000-import` (the Samba share name we created) |
| **Username** | Your Pi username (e.g., `pi`) |
| **Password** | The Samba password you set with `smbpasswd` |
| **Port** | `445` (default SMB port) |

5. Tap **"Test connection"** at the bottom

**Expected result:** You should see "Connection successful" with a list of files in the import directory.

**If connection fails:**
- Double-check the IP address/hostname
- Verify the Samba password is correct
- Make sure both devices are on the same WiFi network
- Check that Samba is running: `sudo systemctl status smbd`

6. Tap **"Save"** in the top right

### Step 2.4: Configure Automatic Transfers (Optional but Recommended)

This is the magic part — photos transfer automatically without your wife touching anything.

1. In PhotoSync, tap the **gear icon** (Settings)
2. Tap **"Auto transfer"**
3. Tap **"Create new auto transfer"**

**Configure the auto transfer:**

**Name:** `SPF5000 Frame`

**Source:**
- Tap **"Select source"**
- Choose **"Camera folder"** or **"All photos"** depending on preference
- If you want only certain folders, select those specifically

**Destination:**
- Tap **"Select destination"**
- Choose **"SPF5000 Frame"** (the companion we created)

**Trigger (when to transfer):**

For most users, I recommend:

- ✅ **"When charging"** — Transfers happen when phone is charging
- ✅ **"When on WiFi"** — Only transfers on home WiFi (no cellular data)
- ✅ **"When connected to specific WiFi"** — Optionally limit to your home network

**Alternative triggers:**

- **"At specific time"** — Transfer at a set time daily
- **"When new photos available"** — Transfer immediately when new photos are taken (uses more battery)

**Transfer options:**

- **"Delete after transfer"** — ❌ **DO NOT ENABLE** — You don't want photos deleted from the phone
- **"Transfer videos"** — Enable if you want videos on the frame too
- **"Transfer RAW"** — Enable if shooting RAW (most users don't need this)

4. Tap **"Save"**

### Step 2.5: Test Manual Transfer

Before relying on automatic transfers, test a manual transfer:

1. In PhotoSync, tap the big **red sync button** in the center
2. Select **1-2 recent photos** from the grid
3. Tap **"Send"** at the bottom
4. Select **"SPF5000 Frame"** as the destination
5. Wait for the transfer to complete

**Verify on the Pi:**

```bash
ls -la /var/lib/spf5000/sources/local-files/import/
```

You should see the transferred photos.

---

## Part 3: Configure SPF5000 to Import Photos

Now that photos are arriving on the Pi, SPF5000 needs to import them.

### Step 3.1: Enable Automatic Scanning (Recommended)

SPF5000 can automatically scan and import new photos:

1. Open a browser on your computer
2. Navigate to `http://<pi-ip>:8000` (e.g., `http://192.168.1.50:8000`)
3. Log in to the admin UI
4. Go to **Sources** page
5. Find the **Automatic Scanning** card
6. Enable one or both options:
   - **Enable scheduled scanning** — Scan on a cron schedule (e.g., every 4 hours)
   - **Enable auto-watch** — Scan immediately when new files are detected

**Recommended setup for PhotoSync:**

- ✅ **Enable auto-watch** with debounce delay of 5-10 seconds
- This will automatically import photos as soon as PhotoSync transfers them
- No manual scanning needed!

### Step 3.2: Manual Scan (Alternative)

If you prefer manual control:

1. Open a browser on your computer
2. Navigate to `http://<pi-ip>:8000` (e.g., `http://192.168.1.50:8000`)
3. Log in to the admin UI
4. Go to **Sources** page
5. Find the **Local Files** card
6. Click **"Scan now"**

SPF5000 will scan the import directory and show how many new photos were discovered.

### Step 3.2: Import Discovered Photos

1. After the scan completes, you'll see the scan results
2. Click **"Import now"**
3. Select which collection to import into (e.g., "All Photos")
4. Click **"Import"**

**Note:** If you enabled auto-watch in Step 3.1, this happens automatically — skip this step.

---

## Part 4: Verify Everything Works

### Step 4.1: End-to-End Test

1. **On the phone:** Take a new photo with the camera app
2. **Wait for PhotoSync to transfer:**
   - If auto-transfer is configured: Put phone on charger, wait 1-2 minutes
   - Or manually trigger transfer in PhotoSync
3. **On the Pi:** Verify the file arrived:
   ```bash
   ls -lt /var/lib/spf5000/sources/local-files/import/ | head -5
   ```
4. **In SPF5000:** Run a scan and import
5. **On the frame:** Verify the photo appears in the slideshow

### Step 4.2: Monitor for Issues

**Check PhotoSync transfer history:**

1. Open PhotoSync on the phone
2. Tap the **clock icon** (History)
3. Verify transfers are completing successfully

**Check SPF5000 logs:**

```bash
sudo journalctl -u spf5000 -f --since "1 hour ago"
```

Look for any errors during scan/import operations.

---

## Troubleshooting

### PhotoSync Can't Connect to Pi

**Symptoms:** "Connection failed" or timeout when testing connection

**Solutions:**

1. **Verify both devices are on the same WiFi network**
   - Phone and Pi must be on the same subnet
   - Guest WiFi networks often block device-to-device communication

2. **Check Samba is running:**
   ```bash
   sudo systemctl status smbd
   ```
   If not running: `sudo systemctl start smbd`

3. **Check firewall:**
   ```bash
   sudo ufw status
   ```
   If active, allow SMB:
   ```bash
   sudo ufw allow samba
   ```

4. **Try IP address instead of hostname:**
   - Some networks don't resolve hostnames properly
   - Use `192.168.1.50` instead of `pictures`

5. **Verify Samba password:**
   ```bash
   sudo smbpasswd -a $USER
   ```
   Reset the password and try again in PhotoSync

### Photos Transfer But Don't Appear on Frame

**Symptoms:** Photos show up in import folder but not in slideshow

**Solutions:**

1. **Run a scan in SPF5000:**
   - Go to Sources → Local Files → Scan now
   - Then Import now

2. **Check file permissions:**
   ```bash
   ls -la /var/lib/spf5000/sources/local-files/import/
   ```
   Files should be readable by the SPF5000 user

3. **Fix permissions if needed:**
   ```bash
   sudo chown -R $USER:$USER /var/lib/spf5000/sources/local-files/import/
   ```

4. **Check SPF5000 logs for errors:**
   ```bash
   sudo journalctl -u spf5000 -f
   ```

### Auto-Transfer Not Working

**Symptoms:** Photos don't transfer automatically

**Solutions:**

1. **Check auto-transfer settings:**
   - Open PhotoSync → Settings → Auto transfer
   - Verify the trigger conditions are met (charging, WiFi, etc.)

2. **Check battery optimization:**
   - Android may be killing PhotoSync in the background
   - Go to Phone Settings → Apps → PhotoSync → Battery
   - Set to "Unrestricted" or "Don't optimize"

3. **Verify WiFi connection:**
   - Auto-transfer only works when connected to specified WiFi
   - Make sure phone is on home network

4. **Check transfer history:**
   - Open PhotoSync → History
   - Look for failed transfers and error messages

5. **Try manual transfer:**
   - If manual works but auto doesn't, it's a trigger/permission issue
   - If neither works, it's a connection issue

### Photos Transfer Slowly

**Symptoms:** Transfers take a long time or timeout

**Solutions:**

1. **Check WiFi signal strength:**
   - Weak WiFi on Pi or phone causes slow transfers
   - Consider Ethernet for the Pi

2. **Reduce transfer size:**
   - In PhotoSync settings, enable "Resize photos"
   - Set max dimension to 1920 or 2560 (matches frame resolution)

3. **Transfer fewer photos at once:**
   - In auto-transfer settings, limit batch size
   - Transfer 10-20 photos at a time instead of 100

4. **Check network congestion:**
   - Other devices streaming/downloading can slow transfers
   - Try transferring at off-peak times

---

## Advanced Configuration

### Resize Photos Before Transfer

To save space and speed up transfers:

1. In PhotoSync, go to **Settings**
2. Tap **"Transfer settings"**
3. Enable **"Resize photos"**
4. Set **Max dimension** to `1920` or `2560` (matches most frames)
5. Set **JPEG quality** to `90%`

### Organize by Date

To organize photos into dated folders:

1. In PhotoSync, go to **Settings**
2. Tap **"Transfer settings"**
3. Enable **"Create subfolders"**
4. Choose format: `yyyy/MM` or `yyyy/MM/dd`

This creates folders like:
```
/var/lib/spf5000/sources/local-files/import/2026/04/photo.jpg
```

SPF5000 will still find and import these photos.

### Multiple Phones

If multiple family members want to contribute photos:

1. Install PhotoSync on each phone
2. Configure each with the same Pi destination
3. Use the same Samba credentials
4. Each phone can have its own auto-transfer settings

### Transfer from iPhone

PhotoSync also works on iOS:

1. Install PhotoSync on iPhone
2. Configure the same SMB companion
3. Auto-transfer works similarly (may need to enable "Background App Refresh")

---

## Maintenance

### Monthly Tasks

1. **Check import folder size:**
   ```bash
   du -sh /var/lib/spf5000/sources/local-files/import/
   ```
   If it's getting large, you may want to clean up after import.

2. **Review transfer history:**
   - Check PhotoSync for any failed transfers
   - Re-transfer any photos that failed

3. **Verify frame is showing new photos:**
   - Check that recent transfers appear in the slideshow

### Yearly Tasks

1. **Update PhotoSync:**
   - Keep the app updated for bug fixes and security patches

2. **Review auto-transfer settings:**
   - Adjust if wife's photo-taking habits change
   - Add/remove triggers as needed

3. **Backup SPF5000:**
   - Use the admin UI to download a database backup
   - Export collections if you want to preserve originals

---

## FAQ

### Q: Can my wife still use Google Photos?

**A:** Yes! PhotoSync transfers copies of photos. Your wife can:
- Use Google Photos normally for backup and sharing
- PhotoSync copies photos to the frame
- Both work independently

### Q: What happens if the Pi is offline?

**A:** PhotoSync will queue transfers and retry when the Pi is back online. No photos are lost.

### Q: Can I transfer only certain albums?

**A:** Yes. In PhotoSync:
- Go to Settings → Auto transfer → Select source
- Choose specific folders/albums instead of "All photos"

### Q: How do I stop transfers temporarily?

**A:** In PhotoSync:
- Open the app
- Tap the big red sync button to disable auto-transfer
- Tap again to re-enable

### Q: Can I transfer photos from cloud services (Dropbox, OneDrive)?

**A:** Yes! PhotoSync Premium supports transferring from:
- Google Photos
- Dropbox
- OneDrive
- Box
- FTP/SFTP servers

Configure these in Settings → Configure companion.

---

## Support Resources

- **PhotoSync Website:** https://www.photosync-app.com
- **PhotoSync Help:** https://www.photosync-app.com/help.html
- **SPF5000 Documentation:** See other guides in `docs/` folder
- **Samba Documentation:** https://www.samba.org/samba/docs/

---

## Quick Reference

### Pi Information (Fill This In)

| Item | Value |
|------|-------|
| Pi Hostname | _______________ |
| Pi IP Address | _______________ |
| Pi Username | _______________ |
| Samba Password | _______________ |
| Import Path | `/var/lib/spf5000/sources/local-files/import/` |
| Samba Share Name | `spf5000-import` |

### PhotoSync Settings (Fill This In)

| Setting | Value |
|---------|-------|
| Companion Name | _______________ |
| Transfer Trigger | ☐ When charging ☐ On WiFi ☐ Specific time |
| Source Folder | ☐ Camera ☐ All photos ☐ Other: _______ |
| Resize Enabled | ☐ Yes (Max: _______ px) |

---

**You're done!** Your wife can now take photos and they'll automatically appear on the frame. 🎉
