# Backup and Export Guide

This guide explains the first-pass backup, restore, and export workflows available in the SPF5000 admin UI.

It covers:

- what the database backup includes
- what the database restore does and does not restore
- how to export original media from a collection
- how to think about migration or cloning with the current V1 feature set

## Open the backup tools

1. Sign in to the SPF5000 admin UI.
2. Open the **Backups** page from the admin sidebar.

That page provides three workflows:

- **Download database backup ZIP**
- **Restore database backup**
- **Download collection ZIP**

## What database backup includes

The database backup ZIP contains the active SPF5000 DecentDB file plus a small manifest file.

In practice, that means it captures DecentDB-backed state such as:

- application settings
- bootstrap and admin-account records
- collection metadata
- asset metadata
- provider and sync metadata
- cached weather and alert state

The ZIP filename looks like:

- `spf5000-database-backup-YYYYMMDDTHHMMSSZ.zip`

Inside the archive you should expect:

- `spf5000.ddb`
- `backup-manifest.json`

## What database backup does not include

Database backup is **not** a full-frame clone.

It does **not** include:

- original media files stored on disk
- generated display variants
- generated thumbnails
- a full Raspberry Pi image or appliance snapshot

That distinction matters because SPF5000 intentionally stores structured state in DecentDB and image binaries on the filesystem.

## Download a database backup

On the **Backups** page:

1. Find the **Database backup** card.
2. Click **Download database backup ZIP**.
3. Save the ZIP somewhere safe.

Recommended practice:

- keep more than one backup over time
- store backups somewhere other than the Pi itself
- take a fresh backup before major changes or migration work

## Restore a database backup

On the **Backups** page:

1. Find the **Restore database backup** card.
2. Choose the backup ZIP you want to restore.
3. Tick the confirmation checkbox acknowledging that the current SPF5000 database will be replaced.
4. Click **Restore database backup**.

SPF5000 validates the ZIP before applying it. Invalid ZIPs, missing database files, or non-SPF5000 database files are rejected with a clear error.

After a successful restore:

- SPF5000 replaces the active DecentDB database
- runtime state is refreshed from the restored database
- your current admin session is cleared
- you must sign in again

## Important restore warning

Database restore does **not** restore original image files.

If the restored database references media that is not present on the target device, the frame may be missing items until you also move or re-import the corresponding originals.

## Startup recovery for an unreadable database

If SPF5000 cannot read the configured DecentDB file during startup, it preserves the unreadable database artifacts instead of overwriting them in place.

During recovery SPF5000:

- moves the current `spf5000.ddb` file plus any `-wal` or `-shm` sidecars into `staging/database-recovery/<timestamp>/` under the configured data root
- logs the recovery location
- creates a fresh database so the app can finish starting

This keeps the unreadable database files available for manual inspection or recovery work. It does **not** automatically repair or merge the preserved database contents into the new database.

## Export original media from a collection

Use collection export when you need the actual image files instead of only the database state.

On the **Backups** page:

1. Find the **Collection export** card.
2. Choose the collection you want to export.
3. Click **Download collection ZIP**.

The ZIP filename looks like:

- `spf5000-collection-<slug>-YYYYMMDDTHHMMSSZ.zip`

The archive contains:

- the exportable original image files for that collection
- `collection-export-manifest.json`

If some originals are missing from managed storage, SPF5000 skips them and records that fact in the manifest. If no exportable originals remain, the export fails instead of giving you a misleading empty media archive.

## Migration and cloning guidance

For V1, think in terms of two separate workflows:

1. **Database backup/restore** moves DecentDB-backed state.
2. **Collection export** moves original image files.

If you want to migrate to another Pi, plan to move both kinds of data. Database restore alone is not enough to recreate the media library on the destination device.

SPF5000 does not yet provide a one-click full-frame clone or complete appliance backup/restore workflow.
