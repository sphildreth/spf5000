# ADR 0020: Use Admin-Protected ZIP Backup/Restore and Media Export

- Status: Proposed
- Date: 2026-03-18

## Context
SPF5000 stores structured app state in DecentDB (ADR 0003), keeps original media files on the filesystem (ADR 0004), and protects admin capabilities behind the single-admin authenticated boundary (ADR 0009). Operators need a practical way to move or recover database state and to export collection media without introducing a misleading "full device clone" promise.

The backup/export architecture needs to preserve the DecentDB-versus-filesystem storage boundary, keep destructive restore behavior behind admin authentication, and make it clear that database backup/restore and collection media export solve different problems.

## Decision
Expose admin-protected ZIP workflows for:

- database export and import/restore
- collection media export

Database backup ZIPs package the active DecentDB file together with manifest metadata describing the backup contents. Database restore accepts a ZIP upload, validates its structure and manifest, safely replaces the active DecentDB file, refreshes runtime state from the restored database, and forces re-authentication because restored admin or session state may no longer match the pre-restore runtime.

Collection export packages the original media files for a chosen collection together with a manifest. This workflow exports collection media only; it does not include DecentDB state.

Product and operator documentation must explicitly distinguish:

- DB-only backup/restore for application state recovery
- collection media export for original files

These workflows are not a full-frame backup, appliance image, or one-step clone/restore feature.

## Consequences
- SPF5000 gains a clear, admin-scoped recovery path for DecentDB state and a separate operator workflow for exporting original collection media.
- The architecture stays aligned with the existing storage split: DecentDB backups remain database-focused while media export reads originals from the filesystem.
- Restore handling must validate ZIP inputs, replace the live database carefully, refresh runtime caches/state, and terminate existing authenticated sessions.
- Operators who need both app state and source media must run both workflows; a complete appliance clone remains out of scope for this ADR.
