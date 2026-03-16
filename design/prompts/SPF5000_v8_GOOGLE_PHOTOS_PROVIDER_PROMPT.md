# SPF5000 Follow-On Implementation Prompt
## Google Photos Provider via Ambient API + Offline-First Local Cache

You are working in the existing `spf5000` repository after the current in-flight work completes.

Your task is to implement **Google Photos support as a first-class source provider** for SPF5000.

This feature is required now and is part of the intended product behavior.

The implementation must follow the project’s established architecture:

- FastAPI backend
- React + TypeScript + Vite frontend
- DecentDB for app settings/state
- offline-first playback
- browser-based fullscreen slideshow
- provider-based source model

---

## Product Goal

The user experience goal is:

1. Admin opens SPF5000 admin UI
2. Admin connects a Google Photos account
3. Google Photos media sources/albums are selected for the device using the correct Google-supported device/ambient flow
4. SPF5000 periodically syncs metadata and downloads playable assets into local managed cache/storage
5. `/display` plays from the local cache, not directly from live cloud URLs
6. If WAN or Google Photos is temporarily unavailable, SPF5000 continues showing cached images

This must feel like:
- a real first-class Google Photos integration
- not a manual export/import workaround
- not a “sync a folder yourself” hack
- not fragile live-cloud slideshow playback

---

## Critical Architectural Requirement

Implement Google Photos support using the **Google Photos Ambient API / device-oriented integration model**, not as a naive legacy “browse arbitrary user albums via the old broad Library API” design.

The provider must fit the repo’s **offline-first** architecture:
- Google Photos is a **source**
- SPF5000 slideshow uses **locally cached** playable assets
- network/cloud is used for **sync/import**, not direct playback

This is a hard requirement.

---

## Non-Goals / Explicitly Not Acceptable

Do **not** implement the final feature as any of the following:

- manual Google Takeout import
- “export album to a local folder and point LocalFilesProvider at it”
- live-only cloud slideshow playback
- a design that requires the display route to depend on Google API calls during transitions
- a legacy broad-library browsing design that assumes unrestricted access to all user albums/media

Those may be temporary local testing aids if absolutely necessary, but they are not the implemented feature.

---

## High-Level Requirements

Implement:

1. `GooglePhotosProvider` backend provider
2. provider settings/state persistence in DecentDB
3. OAuth/account connection flow
4. device/provider lifecycle management
5. source/collection selection flow aligned to the Google-supported device/ambient model
6. sync/import pipeline into local managed storage/cache
7. admin UI for connect/disconnect/status/source selection
8. playback integration so Google Photos assets become ordinary cached display assets
9. documentation and ADR/SPEC updates

---

## 1. Provider design

Add a new provider implementation for Google Photos.

Suggested structure:

```text
backend/app/providers/google_photos/
```

Suggested components:
- `provider.py`
- `client.py`
- `oauth.py`
- `models.py`
- `sync.py`
- `mapping.py`
- `errors.py`

If the repo already has a provider structure, integrate cleanly with it.

The provider must behave like a first-class `PhotoSourceProvider` implementation, not as a one-off special case.

It should fit the existing provider abstraction or evolve that abstraction cleanly if needed.

---

## 2. DecentDB persistence

Persist Google Photos provider state in DecentDB.

At minimum persist:
- provider record
- provider enable/disable state
- linked Google account identity metadata as appropriate
- OAuth token metadata / refresh token / expiration metadata
- selected Google Photos source mappings
- sync cursors/checkpoints/state
- imported asset metadata
- last successful sync time
- sync errors/status
- asset-to-local-cache mapping

Do **not** store actual image binaries in DecentDB.
Store image files in the local managed cache/storage and metadata/state in DecentDB.

Use explicit SQL and repository methods aligned with the existing project style.

---

## 3. OAuth / connection flow

Implement an admin-managed Google Photos connection flow.

Requirements:
- admin initiates provider connection from the admin UI
- backend starts the Google auth/authorization flow
- callback is handled cleanly
- provider account becomes linked to SPF5000 after successful auth
- admin can see connection status
- admin can disconnect provider if desired

Design requirements:
- use a clean service/repository structure
- do not hardcode secrets in code
- integrate with runtime config/environment in a sane way for OAuth client configuration
- keep implementation understandable

The provider should expose a clear connected/disconnected/error state.

---

## 4. Source / collection selection

Implement the source-selection workflow so the user can choose the Google Photos content that SPF5000 should display.

Requirements:
- user/admin can see available Google Photos media sources/collections relevant to the device-oriented integration model
- user/admin can enable one or more sources for SPF5000
- the mapping between selected Google sources and SPF5000 display assets is persisted
- selection changes affect future sync behavior

The UX should be appliance-oriented:
- connect account
- choose what the frame should show
- let SPF5000 sync and display it

Avoid exposing unnecessary raw API details in the UI.

---

## 5. Sync / import model

This is the most important runtime rule:

SPF5000 must **sync/import** Google Photos content into local managed storage/cache.

It must **not** depend on live Google API calls for normal slideshow transitions.

### Required behavior
- periodic sync job fetches provider metadata
- sync job identifies new/updated/removed provider assets as appropriate
- playable image assets are downloaded into local cache/storage
- display-ready local metadata is created/updated
- slideshow consumes local cached assets through the normal display pipeline

### Required resilience
- if Google Photos is temporarily unavailable, cached assets continue to display
- if sync fails, the slideshow should still work with already-cached images
- sync errors should be surfaced in admin UI without breaking display playback

### Suggested implementation shape
- provider sync service
- sync job runner or background task pattern
- local asset ingestion pipeline
- reuse of existing asset/cache abstractions where possible

---

## 6. Playback integration

Once Google Photos assets are synced locally, the slideshow should not care whether they came from:
- local files
- Google Photos
- future providers

The display route should use the same ordinary local playback model.

Requirements:
- synced Google assets appear as normal playable slideshow assets
- existing slideshow transitions and no-flicker behavior remain intact
- sleep schedule behavior remains intact
- boot/loading/empty-state logic remains consistent

Do not create a separate “cloud display mode.”

---

## 7. Admin UI

Add admin UI support for Google Photos provider management.

At minimum support:
- provider status card/page
- connect Google Photos action
- disconnect action
- linked account summary
- source selection UI
- sync status display
- last successful sync display
- current error/warning display if sync fails

Keep the UI simple and understandable.
Do not build a giant cloud-provider dashboard.

Suggested admin flow:
1. Go to Sources / Providers
2. Add or connect Google Photos
3. Authenticate
4. Select source(s)
5. Save
6. See sync status

---

## 8. Sync scheduling / triggers

Implement a practical sync strategy.

At minimum support:
- manual sync trigger from admin UI
- automatic periodic sync on a reasonable cadence
- startup sync or deferred startup reconciliation if appropriate

The sync strategy should not block slideshow rendering.
Use background work / queued task patterns already consistent with the repo.

Keep it simple and robust.

---

## 9. Error handling

Implement clear but non-scary error handling.

Requirements:
- provider connection failures are surfaced clearly in admin UI
- token/auth expiration issues are surfaced clearly
- sync failures do not break local slideshow playback
- provider can recover after reconnect/re-auth
- logs are useful for troubleshooting

Avoid:
- raw traceback dumps in normal UI
- silent broken states
- crashing the display pipeline because Google is unavailable

---

## 10. Runtime / config expectations

Keep OAuth/runtime bootstrap details in the appropriate runtime config layer, not in DecentDB if they are deployment secrets.

A reasonable split:

### Runtime config / env / `spf5000.toml`
- Google OAuth client ID
- Google OAuth client secret
- callback base URL if needed
- provider feature enablement flags if needed

### DecentDB
- linked account state
- refresh/access token metadata
- sync state
- source selections
- imported asset metadata
- provider status

Do not put user-editable provider selections into runtime config.

---

## 11. Suggested schema areas

Add or evolve storage for:
- `providers`
- `provider_accounts`
- `provider_source_mappings`
- `provider_sync_runs`
- `provider_sync_errors`
- `provider_assets`
- `provider_asset_files`

You may choose different names, but keep the schema understandable and aligned with project style.

The key idea:
- provider integration state lives in DB
- local playable assets live on disk
- mapping between them is explicit

---

## 12. Testing

Add useful tests.

Priority areas:
- provider state transitions
- repository behavior
- token/account persistence behavior
- sync logic and asset ingestion mapping
- playback integration assumptions
- failure handling when remote provider is unavailable

If full end-to-end Google integration tests are impractical, create:
- service-layer tests
- repository tests
- client abstraction tests with mocks/fakes
- sync pipeline tests around deterministic provider payloads

The code should be structured to make testing feasible.

---

## 13. Documentation updates

Update documentation so Google Photos support is explicit and correctly described.

At minimum update:
- `README.md`
- `design/PRD.md`
- `design/SPEC.md`
- `design/ARD.md`

Update or add ADRs to reflect:
1. Google Photos is implemented as a first-class provider
2. provider playback is offline-first via local cache
3. Google integration uses device/ambient-oriented model rather than live cloud slideshow playback
4. synced provider assets are normalized into the local slideshow pipeline

Also add or update user-facing documentation under `docs/` if appropriate, such as:
- how to configure Google provider credentials
- how to connect Google Photos
- how source selection works
- how sync/offline playback behaves

---

## 14. Constraints / Non-Goals

Do not:
- bypass the provider abstraction just to get Google working quickly
- make the slideshow directly dependent on live Google API calls
- overcomplicate the UI
- require the user to manually export/import albums as the official solution
- weaken the offline-first design

The implementation should feel like a natural extension of SPF5000, not a bolted-on hack.

---

## 15. Acceptance Criteria

This work is complete when:

- Google Photos exists as a first-class provider in the backend
- admin can connect/disconnect Google Photos from the admin UI
- source/collection selection is supported through the intended device/provider flow
- selected Google content is synced into local managed cache/storage
- synced content appears in the normal slideshow playback pipeline
- slideshow continues working from local cache when Google is unavailable
- sync status/errors are visible in admin UI
- DecentDB persists provider state and sync metadata
- docs and ADR/SPEC updates are complete

---

## 16. Implementation Notes

Favor:
- provider abstraction discipline
- offline-first architecture
- local cached playback
- simple admin UX
- explicit state transitions
- clean repositories/services

Avoid:
- shortcut designs that violate the architecture
- “just make it work” direct cloud playback
- leaking Google-specific complexity all over the codebase

Build the simplest good first-class Google Photos provider.
