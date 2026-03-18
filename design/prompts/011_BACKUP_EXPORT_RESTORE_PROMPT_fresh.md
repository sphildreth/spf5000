# SPF5000 Follow-On Implementation Prompt
## Backup, Restore, Database Export/Import, and Library ZIP Download

You are working in the existing `spf5000` repository after the current in-flight work completes.

Your task is to implement a **backup and export system** for SPF5000.

This feature should make it easy to:

1. back up the SPF5000 DecentDB database and related settings
2. restore SPF5000 from a backup
3. download/upload the `.ddb` database file as a ZIP
4. export all images from a library/collection as a single ZIP
5. make cloning or migrating a frame to another Pi practical

This must integrate cleanly with the existing SPF5000 architecture:

- FastAPI backend
- React + TypeScript + Vite frontend
- DecentDB for settings/state
- local filesystem storage for images and derived assets
- admin-auth-protected management UI

---

## Product Goal

SPF5000 should support appliance-friendly backup and export behavior.

The admin should be able to:

- download a ZIP containing the current DecentDB database
- upload a ZIP to restore a DecentDB database
- create a broader backup/export workflow suitable for migration or cloning
- download all images in a selected library/collection as one ZIP
- move the setup to another device without hand-copying files

This should feel like a product feature, not a manual SSH task.

---

## Scope

Implement the following:

1. database ZIP download
2. database ZIP upload/restore
3. collection/library image ZIP export
4. admin UI for backup/export operations
5. backend service/repository support
6. documentation and ADR/SPEC updates

Optional but encouraged:
- lightweight metadata manifest in export ZIPs
- validation and safety checks before restore
- backup history/audit metadata

---

## High-Level Requirements

## 1. DecentDB backup/export

Add the ability to download the current SPF5000 `.ddb` database file as a ZIP.

Requirements:
- admin-auth protected
- creates ZIP on demand
- ZIP contains the `.ddb` file
- filename should be sensible and timestamped
- response should stream or otherwise handle download cleanly

Suggested ZIP naming:
- `spf5000-db-backup-YYYYMMDD-HHMMSS.zip`

Suggested contents:
- `spf5000.ddb`

### Optional but recommended
Also include a small metadata manifest file such as:
- `backup-manifest.json`

This manifest may contain:
- SPF5000 version
- backup timestamp
- hostname or frame name if available
- schema/app version if known

---

## 2. DecentDB upload/restore

Add the ability to upload a ZIP containing a `.ddb` file and restore it into SPF5000.

Requirements:
- admin-auth protected
- only accepts supported ZIP structure
- validates that the ZIP contains exactly or at least one valid `.ddb` file
- safely replaces or imports the database according to chosen restore model
- clear error messages for invalid uploads
- avoid partial/unsafe writes

### Safety requirements
Restoring a database is a potentially destructive action.

Implement a careful process:
- validate upload
- extract to temp location
- confirm `.ddb` presence
- optionally verify file extension and non-empty file
- stop or pause DB usage as needed
- replace active DB file safely
- restart or refresh application state as needed

### Recommended UX
Require an explicit confirmation step or checkbox in the UI such as:
- “I understand this will replace the current SPF5000 database.”

---

## 3. Broader backup/restore thinking

At minimum, database ZIP backup/restore must exist.

Also design the implementation so it can evolve into fuller backup/restore later.

Reason:
The `.ddb` file contains settings/state, but the actual images may live on disk outside the database.

So this slice should at least:
- support DB backup/restore now
- document the difference between DB-only backup and full media backup
- keep the design open for future “full frame backup” functionality

Do not falsely imply that DB-only restore restores all local media files unless that is actually implemented.

---

## 4. Library/collection image ZIP download

Add the ability to download all images belonging to a selected library or collection as a single ZIP file.

Requirements:
- admin-auth protected
- choose a collection/library
- ZIP includes all original image files associated with that collection
- filenames should be stable and reasonable
- export should skip missing/broken files gracefully and report useful errors if needed

Suggested ZIP naming:
- `spf5000-library-<slug>-YYYYMMDD-HHMMSS.zip`
- `spf5000-collection-<slug>-YYYYMMDD-HHMMSS.zip`

### Optional but recommended
Include a manifest file inside the ZIP with:
- collection name
- export timestamp
- item count
- file list
- source/provider metadata if helpful

This makes exports easier to reason about later.

---

## 5. Collection/library model compatibility

Use the existing SPF5000 data model and naming cleanly.

If the current codebase uses:
- “library”
- “collection”
- “album”
- “source-mapped collection”

adapt the implementation to the real model, but preserve the intended feature:

> download all images in a chosen logical group as one ZIP

Do not invent conflicting terminology if the repo already has a clear concept.

---

## 6. Backend API

Add backend endpoints for backup/export functionality.

Suggested route shapes:

### Database backup/restore
- `POST /api/admin/backup/database/export`
- `POST /api/admin/backup/database/import`

or alternatively:
- `GET /api/admin/backup/database/download`
- `POST /api/admin/backup/database/upload`

### Library/collection export
- `POST /api/admin/export/collections/{id}/download`

You may adapt the route naming to fit the existing admin API style.

Requirements:
- admin-auth protected
- correct content type / file download behavior
- robust validation
- clear error handling

---

## 7. Admin UI requirements

Add an admin UI section for backup/export operations.

Suggested sections:

### Backup / Restore
- Download database backup
- Upload database backup
- Restore warning/confirmation
- small explanation of what DB backup includes and does not include

### Collection / Library Export
- choose collection/library
- download ZIP of all images
- show collection name and item count if available

### Nice-to-have
A short explanation:
- DB backup restores settings/state
- image ZIP export is for media extraction
- full media restore may require future broader backup support

Keep the UI straightforward and safe.

---

## 8. File handling and security

Implement careful file handling.

Requirements:
- use temporary files/directories safely
- limit upload to ZIP only for DB restore endpoint
- validate ZIP contents before applying restore
- protect against trivial path traversal in ZIP extraction
- do not trust uploaded filenames blindly
- clean up temporary files

For image ZIP downloads:
- do not include paths outside intended media roots
- do not expose arbitrary filesystem traversal

Keep the implementation conservative and explicit.

---

## 9. Concurrency and restore behavior

A database restore may conflict with running application state.

Implement a sensible strategy.

Possible approach:
- acquire an app-level restore/export lock
- block concurrent destructive operations
- ensure DB file is not being swapped in an unsafe way
- reinitialize repositories/services after restore if needed

The restore flow must not leave SPF5000 half-broken.

Document the chosen strategy.

---

## 10. Persistence / manifests

Recommended manifests:

### Database backup manifest
`backup-manifest.json`
Suggested fields:
- backup type
- created timestamp
- SPF5000 version
- hostname/frame name
- db filename

### Collection export manifest
`collection-export-manifest.json`
Suggested fields:
- export type
- collection/library id
- collection/library name
- created timestamp
- item count
- file list

These are optional but strongly encouraged.

---

## 11. Error handling

Provide clear, non-scary admin-facing errors for:
- invalid ZIP upload
- missing `.ddb` file in ZIP
- restore failure
- download/export failure
- collection contains missing files
- insufficient permissions
- file too large if limits are added

Do not dump raw stack traces into the normal admin UI.

Log details server-side.

---

## 12. Testing

Add useful tests for:
- ZIP creation for DB backup
- ZIP validation for DB restore
- restore rejection on invalid ZIPs
- safe handling of ZIP contents
- collection export ZIP creation
- missing-file handling
- endpoint auth protection

If full integration tests are difficult, prioritize service-layer and API tests.

---

## 13. Documentation updates

Update the relevant documentation.

At minimum update:
- `README.md`
- `design/PRD.md`
- `design/SPEC.md`
- `design/ARD.md`

Also update or add user-facing docs under `docs/` for:
- how to back up the database
- how to restore from backup
- what DB restore includes and does not include
- how to export a collection/library as ZIP

Add or update ADRs for:
1. database backup/restore as a first-class admin feature
2. ZIP-based export/import approach
3. distinction between database backup and media export

Keep ADRs concise and decision-focused.

---

## 14. Constraints / Non-Goals

Do not:
- pretend DB backup is a full media backup unless it actually is
- overwrite the active database recklessly
- implement a giant backup orchestration framework
- expose backup/restore endpoints without admin protection
- allow arbitrary filesystem zip-up/download behavior

Keep this feature:
- safe
- understandable
- migration-friendly
- appliance-oriented

---

## 15. Acceptance Criteria

This work is complete when:

- admin can download the current `.ddb` as a ZIP
- admin can upload a ZIP and restore a `.ddb` safely
- restore flow validates inputs and handles failure cleanly
- admin can download all images in a chosen collection/library as one ZIP
- generated ZIPs have sensible names
- admin UI supports these workflows
- docs and ADR/SPEC updates are complete

Optional but strongly preferred:
- manifests included in ZIPs
- restore confirmation UX
- clean reinitialization after restore

---

## 16. Implementation Notes

Favor:
- safe file handling
- explicit validation
- admin clarity
- migration usefulness
- predictable ZIP structure

Avoid:
- hidden destructive actions
- sloppy temp-file handling
- coupling backup logic tightly to one specific collection/provider type
- confusing DB backup with complete frame cloning unless fully implemented

Build the simplest good first version.
