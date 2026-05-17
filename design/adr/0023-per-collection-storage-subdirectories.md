# ADR 0023: Per-Collection Storage Subdirectories

## Status

Accepted

## Context

SPF5000 currently stores all original image files in a single global `originals/` directory. Collections are purely logical groupings — assets share the same storage regardless of which collections they belong to. This design has served well for initial development but creates two limitations:

1. **Visibility**: The admin UI has no way to show users where a collection's media is stored, since there is no per-collection storage location.
2. **Data management**: Moving collection media requires manual filesystem operations outside the admin UI.

## Decision

We will add a `storage_path` field to collections. When set, assets imported into that collection will be stored in a subdirectory under the global originals directory, named after the collection ID:

```
storage/
  originals/
    {collection_id}/
      {asset_filename}
```

If `storage_path` is `null` or empty, assets fall back to the global `originals/` directory (backward compatible).

The system will:
- Store each collection's assets in `storage/originals/{collection_id}/`
- Allow administrators to set a custom storage path per collection from the admin UI
- Automatically create the subdirectory on first import if it doesn't exist
- Default to `originals/{collection_id}/` when no custom path is specified
- Validate that custom paths are within the `storage/originals/` hierarchy for safety

## Changes Required

### Backend

1. **Collection model** (`backend/app/models/collection.py`): Add `storage_path: str | None` field
2. **Repository** (`backend/app/repositories/collection_repository.py`): Add `storage_path` to queries and updates
3. **Schema** (`backend/app/schemas/collection.py`): Add `storage_path` to request/response models
4. **Asset ingest service** (`backend/app/services/asset_ingest_service.py`): Use collection's storage path when storing originals
5. **LocalFilesProvider** (`backend/app/providers/local_files.py`): Ensure path is under `sources_root_dir` — extend scope to include `storage/originals/` as well

### Frontend

1. **Types** (`frontend/src/api/types.ts`): Add `storage_path` to `CollectionSummary` and related types
2. **API client** (`frontend/src/api/collections.ts`): Include `storage_path` in requests
3. **CollectionsPage** (`frontend/src/pages/CollectionsPage.tsx`): Display and edit storage path for each collection

### Database

1. Add `storage_path` column to `collections` table (nullable, default NULL)

## Consequences

### Positive
- Users can see and modify where each collection's media is stored
- Easier to manage storage by moving collection directories
- Clearer separation of collection media at the filesystem level

### Negative
- Existing assets remain in `originals/` unless migrated (out of scope for V1)
- Must ensure `LocalFilesProvider` validates paths correctly to prevent accidental storage outside the hierarchy

## Notes

- This is a backward-compatible change — existing collections with `storage_path = NULL` continue using the global directory
- Migration of existing assets to new collection directories is out of scope for this ADR
- The admin UI should show the effective storage path (either custom or derived from collection ID)