# Google Photos Setup Guide

This guide walks through the complete Google Photos setup flow for SPF5000.

It covers:

- creating the required Google Cloud credentials
- adding those credentials to `spf5000.toml`
- connecting a Google account from the SPF5000 admin UI
- selecting the Google Photos album or ambient source the frame should display
- running the first sync
- switching the slideshow to the synced Google Photos collection
- understanding offline playback, sync behavior, and troubleshooting

## What this integration does

SPF5000 treats Google Photos as a first-class source provider, but it does **not** stream slides directly from Google during playback.

Instead, the flow is:

1. SPF5000 starts Google's device approval flow.
2. You approve the frame from another device.
3. SPF5000 creates a Google Photos Ambient device for the frame.
4. You choose what the frame should show from Google's own selection UI.
5. SPF5000 syncs those photos into managed local storage.
6. The `/display` route plays from the local cache.

That means the frame can keep showing already-synced photos even if your WAN connection or Google Photos is temporarily unavailable.

## Before you start

Make sure you have:

- a working SPF5000 installation
- access to the SPF5000 admin UI
- a Google account that owns or can access the photos you want to display
- permission to create or edit a Google Cloud project
- access to the SPF5000 runtime config file

Typical config file locations:

- development checkout: `./spf5000.toml`
- Pi appliance install: `/var/lib/spf5000/spf5000.toml`

It is also strongly recommended that you set a stable `security.session_secret` in `spf5000.toml` so admin sessions survive backend restarts.

## Step 1: Create Google Cloud credentials

SPF5000 uses the Google Photos Ambient API with the OAuth 2.0 device flow for TVs and limited-input devices.

In Google Cloud Console:

1. Create a new project or choose an existing one.
2. Enable the **Google Photos Ambient API** for that project.
3. If Google prompts you to configure the OAuth consent screen, complete that step first.
4. Create an **OAuth client ID**.
5. Choose the application type **TVs and Limited Input devices**.
6. Copy the generated `client_id`.
7. Copy the generated `client_secret`.

Important notes:

- SPF5000 currently expects **both** `client_id` and `client_secret`.
- This device-flow client does not use a browser redirect callback in SPF5000.
- Keep the client secret private. Treat it like any other deployment secret.

## Step 2: Add the credentials to `spf5000.toml`

Edit your SPF5000 runtime config and add or update the Google Photos block:

```toml
[security]
session_secret = "replace-with-a-long-random-string"

[providers.google_photos]
client_id = "your-google-client-id"
client_secret = "your-google-client-secret"
provider_display_name = "Google Photos"
sync_cadence_seconds = 3600
```

Field meanings:

- `client_id`: Google OAuth client ID for the Ambient API device flow
- `client_secret`: matching Google OAuth client secret
- `provider_display_name`: label SPF5000 uses in the UI and for the managed Google collection
- `sync_cadence_seconds`: automatic sync interval in seconds; `3600` means roughly hourly

SPF5000 requests:

- `openid`
- `email`
- `profile`
- `https://www.googleapis.com/auth/photosambient.mediaitems`

Those let SPF5000 show a linked account summary and sync the selected Google Photos media into the local cache.

## Step 3: Restart SPF5000

After editing the config, restart the backend so it picks up the new credentials.

Common restart patterns:

### Development

If you run SPF5000 from a source checkout:

```bash
make backend
```

If the backend is already running, stop and start it again after saving `spf5000.toml`.

### Raspberry Pi appliance install

```bash
sudo systemctl restart spf5000
```

If you changed the Pi-managed config file under `/var/lib/spf5000/`, restart the service after every credential update.

## Step 4: Connect Google Photos from the admin UI

Once the backend restarts:

1. Sign in to the SPF5000 admin UI.
2. Open the **Sources** page.
3. Find the **Google Photos** card.
4. Click **Connect Google Photos**.

SPF5000 will show:

- a Google verification URL
- a user code
- the time the code expires
- the polling interval guidance

From another device, such as your phone or laptop:

1. Open the verification URL.
2. Enter the displayed code.
3. Approve access for the Google account you want this frame to use.

Then return to SPF5000 and click:

- **Check approval**, or
- **Refresh approval status**

When the connection succeeds, the Sources page should show:

- a connected account summary
- the Google Photos device section
- a Google Photos settings link

## Step 5: Choose the Google Photos album or source

After SPF5000 links the Google account, it creates a Google Photos Ambient device and stores the returned `settingsUri`.

On the Sources page:

1. Click **Open Google Photos settings**.
2. Use Google's selection UI to choose what the frame should display.
3. Save the selection in Google's UI.
4. Return to SPF5000.

This is where you choose the actual **Google Photos album** for the frame.

Important behavior:

- SPF5000 intentionally relies on Google's own source-selection UI instead of recreating a full Google Photos browser inside the admin app.
- The selections shown back in SPF5000 come from the Ambient device state that Google returns to the backend.
- You can revisit the same Google settings link later to change album selection.

## Step 6: Run the first sync

After selecting the album or source:

1. Return to the Google Photos card on the Sources page.
2. Click **Sync now**.
3. Watch the **Latest sync run** section.

Useful status fields:

- **Cached assets**: how many synced Google items currently exist in the local cache
- **Last successful sync**: last completed successful provider sync
- **Imported / Updated / Removed / Skipped / Errors**: latest sync counters

If the sync says no media sources are selected yet, go back to the Google settings page, finish the selection there, and run sync again.

## Step 7: Make the slideshow use the Google Photos collection

Syncing Google Photos imports the files into SPF5000's normal local asset pipeline, but the slideshow still follows the currently selected display collection.

If you want the frame to show only your synced Google Photos content:

1. Open **Display Settings** in the admin UI.
2. Find the selected collection setting.
3. Choose the collection named **Google Photos** (or your configured `provider_display_name`).
4. Save the display settings.

After that, the `/display` route will use the synced Google Photos collection like any other local collection.

If you keep another collection selected, the slideshow will continue using that collection instead.

## How sync and offline playback work

Google Photos in SPF5000 is designed to be offline-first.

### What gets stored where

`spf5000.toml` stores:

- Google OAuth client ID
- Google OAuth client secret
- provider display name
- sync cadence

DecentDB stores:

- linked account summary
- access/refresh token state
- Google device state
- selected media sources returned by Google
- sync history
- remote-to-local asset mappings

The filesystem stores:

- downloaded originals
- generated display variants
- generated thumbnails
- staging files used during sync

### What the display route uses

The slideshow does **not** call the Google Photos API for normal transitions.

It uses the same local playlist and local cached files as every other SPF5000 asset source.

### Automatic sync behavior

SPF5000 supports:

- manual sync from the Sources page
- automatic periodic sync based on `sync_cadence_seconds`
- startup/background sync coordination

### Disconnect behavior

Disconnecting Google Photos removes the live account/device association, but it does **not** delete already cached local assets.

That is intentional so offline playback can continue until you explicitly change collections or remove content some other way.

## Security notes

- Do not commit real Google credentials into the repository.
- Restrict read access to your runtime config file.
- Protect the SPF5000 data directory because it contains provider state and cached local media.
- Use a stable `security.session_secret` so admin sessions are properly signed across restarts.

## Troubleshooting

### The Google Photos card says "not configured"

Check `spf5000.toml` and verify:

- `[providers.google_photos]` exists
- `client_id` is set
- `client_secret` is set

Then restart the backend.

### The approval code expired

Start the connection again from the Sources page. Device-flow approval codes are time-limited.

### The account connected, but no photos appear

Check all of the following:

1. You opened the Google Photos settings link and selected an album or source.
2. You ran **Sync now** after making the selection.
3. The sync run shows imported or cached assets.
4. The active display collection is set to **Google Photos** on the Display Settings page.

### The sync completes, but the slideshow still looks unchanged

Most often, the display is still pointing at a different collection. Switch the active display collection to the Google Photos collection.

### SPF5000 warns about `Highlights`

Google Photos `Highlights` may appear in the returned source list, but SPF5000 currently warns about it because the Ambient API does not support normal per-source enumeration for that selection in the same way as albums.

If you want predictable synced results, prefer explicit albums or other clearly selectable sources from Google's settings UI.

### I changed the selected Google album, but the frame still shows old photos

After changing the selection in Google's settings page:

1. return to SPF5000
2. run **Sync now**
3. wait for the latest sync to finish

Previously cached files can remain on disk, but active collection membership follows the latest synced provider state.

### Where should I look for logs?

Common places:

- development backend console output
- Pi appliance service logs:

```bash
sudo journalctl -u spf5000 -f
```

## Quick reference

- Runtime config: `spf5000.toml`
- Pi runtime config: `/var/lib/spf5000/spf5000.toml`
- Admin page: **Sources**
- Manual sync button: **Sync now**
- Display collection setting: **Display Settings**
- Related docs:
  - [`README.md`](../README.md)
  - [`docs/PI_SETUP_GUIDE.md`](./PI_SETUP_GUIDE.md)
  - [`design/adr/0012-use-google-photos-ambient-api-for-offline-first-local-sync.md`](../design/adr/0012-use-google-photos-ambient-api-for-offline-first-local-sync.md)
