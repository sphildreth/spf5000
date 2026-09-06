# ADR 0024: Server-Owned Persisted Shuffle Bag for Slideshow Playback

- Status: Accepted
- Date: 2026-09-05

## Context

The admin UI advertises a specific playback guarantee for shuffle mode. `DisplaySettingsPage` labels it "Show all before repeating" and describes it as *"Each photo is shown once before repeats, with the next cycle avoiding the most recently shown images."* For a 500-photo library this means 500 distinct photographs between repeats.

Field reports were that the frame repeats photographs long before the library has been exhausted, often repeating more than once per pass.

Investigation established that the client-side shuffle bag implemented in `frontend/src/hooks/useSlideshowEngine.ts` is algorithmically correct in isolation. A 500-item run that is never interrupted produces exactly 500 distinct photographs before the first repeat. The defect is not the shuffle; it is the **lifetime of the bag**:

1. `bootPlaylist()` called `resetShuffleBagState()` unconditionally, discarding the partially drained bag (hundreds of photographs that had not yet been shown) together with the recently-shown guard. `DisplayPage` re-enters `bootPlaylist()` from its 60-second poll whenever the currently displayed photograph has left the refreshed playlist (`currentIndex === -1`), which auto-scan and auto-watch produce routinely when a source file disappears and `deactivate_asset_if_unassigned()` sets `assets.is_active = 0`. Measured collapse: one re-boot every 60 slides reduced distinct photographs before the first repeat from 500 to 66; every 30 slides reduced it to 37.
2. Bag state lived only in React `useRef`s, so it was lost on every reload, crash, and kiosk restart.
3. Bag entries were consumed by `shift()` *before* the photograph was loaded, so every aborted transition (in-flight transition guard, or `preloadImage()` rejection) permanently discarded a photograph that was never displayed.
4. `shuffle_bag_enabled` was read nowhere in any ordering decision. `usesShuffleBag()` returned `shuffle_enabled` and ignored it; the backend only stored, echoed, and hashed it. Its defaults also disagreed across layers: `1` in `DEFAULT_SETTINGS`, `True` in `FrameSettings`, `False` in `SettingsUpdateRequest`, `false` in `api/settings.ts`, and `true` in `api/display.ts`.

Client-side persistence is not an available remedy on this product. The deployed kiosk launches Chromium from `deploy/autostart/spf5000-kiosk-launch.sh.template` with `--incognito` and no `--user-data-dir`, so the display browser runs an off-the-record profile and `localStorage` is discarded on exit. The browser is therefore structurally incapable of remembering playback progress across the restarts that a household appliance actually experiences. Any durable no-repeat guarantee must be held by the backend.

## Decision

**The backend owns slideshow ordering and persists it in DecentDB.** `/display` becomes a position-tracking consumer of a server-produced order instead of an owner of playback state.

### Storage

Persist one row per playable scope in a new `display_playback_state` table, created idempotently by the existing `TABLE_STATEMENTS` mechanism in `backend/app/db/bootstrap.py`:

```
display_playback_state
  collection_key text primary key   -- collection id, or '*global*' when no collection is selected
  mode           text not null      -- ordering policy the cycle was dealt for
  cycle_id       text not null      -- changes when a new cycle is dealt
  order_json     text not null      -- permutation of eligible asset ids for the current cycle
  position       integer not null   -- index into order_json of the next photograph to show
  updated_at     text not null
```

This follows ADR `0003`: DecentDB remains the store for application state, and persistence stays explicit in a repository rather than leaking into services or routes.

### Ordering policy

`DisplayService.get_playlist()` resolves the eligible asset set and then produces `items` in **playback order**, accompanied by `playback_position` — the index within `items` of the next photograph to show.

- `shuffle_enabled` and `shuffle_bag_enabled` — the persisted cycle applies. `items` is the cycle permutation; `playback_position` is the persisted cursor.
- `shuffle_enabled` and not `shuffle_bag_enabled` — unbounded random order, dealt fresh when a cycle is created. Repeats are permitted; this preserves the legacy behaviour for anyone who turns the bag off.
- not `shuffle_enabled` — `imported_at desc`, walked forward and wrapped at the end. This is the "Sequential loop" the admin UI names.

A cycle rolls over to a newly dealt permutation when `position` reaches the end of `order`. Reads roll the cycle over and persist it; the client never decides when a cycle ends.

### Reconcile, never reset

When the eligible set changes, the persisted cycle is **reconciled rather than discarded**, so library changes cannot destroy a partially completed pass:

- identifiers no longer eligible are dropped
- identifiers already shown stay before the cursor
- newly eligible identifiers are inserted at random offsets within the first tenth of the remaining queue, bounded by a floor of ten slots, so new photographs surface within a few minutes instead of waiting a full cycle

The last point replaces the previous undocumented behaviour of hoisting every asset imported in the last 24 hours to the front of the playlist, which the client then ignored anyway because its bag was identifier-based.

### Progress reporting

`POST /api/display/playlist/progress` accepts `{ collection_id, asset_id }` and advances `position` to just past `asset_id`. It is idempotent, and it never moves the cursor backwards within a cycle. The display reports **after a transition commits**, so a photograph that failed to load, or a transition that was superseded, does not consume a position.

`GET /api/display/playlist` and the progress endpoint remain public, consistent with the public `/display` runtime and ADR `0009`.

### Caching

The existing playlist LRU cache is retained. `cycle_id` joins the cache key and the playlist revision input so that a rollover cannot be served from a pre-rollover entry. `playback_position` is read live and overlaid when a cached playlist is returned, so per-slide progress writes do not invalidate the cached asset ordering.

### Client responsibilities

`/display` no longer shuffles, no longer keeps a bag, and no longer maintains a recently-shown guard. It walks `items` forward from `playback_position`, reports each committed photograph, and re-fetches when it reaches the end of the list. `bootPlaylist()` must not reset playback state; it starts from `playback_position` and otherwise preserves the photograph on screen. The client-side bag, `SHUFFLE_BAG_RECENT_LIMIT`, `buildShuffleBagAssetIds()`, and the client-side priority queue that raced the server over ordering are removed, leaving exactly one ordering authority.

`shuffle_bag_enabled` becomes a real setting: the backend honours it when dealing a cycle, and the contradictory layer defaults are reconciled to a single default of enabled. The client helper that read it, `usesShuffleBag()`, is deleted along with the bag rather than rewired.

## Consequences

- The no-repeat guarantee now survives the events that actually occur on an appliance: browser crashes, power loss, kiosk restarts, nightly reboots, and library changes.
- A restart resumes mid-cycle instead of restarting the pass. Up to one photograph can be repeated after an unclean exit — the photograph that was on screen but had not yet been reported — which is bounded and far smaller than the previous full-cycle loss.
- The backend performs roughly one small single-row update per slide (one every 30 seconds at the default interval). This is deliberate and bounded; it is not a per-frame or per-poll write.
- Progress reporting adds one lightweight localhost `POST` per slide. The slideshow never blocks on it; a failed report degrades to at most one repeated photograph on the next resume.
- A single appliance has exactly one display client, so no cross-client coordination or locking is introduced. Concurrent displays would need a follow-up decision.
- Removing the client-side bag and priority queue deletes a body of subtle code, and makes server order the single source of truth for what plays next, which is what the playlist endpoint's name already implies.
- Turning `shuffle_bag_enabled` off now genuinely yields unbounded random playback, so administrators get the behaviour the setting's name promises.
- The admin UI's "Show all before repeating" copy is now an accurate description of shipped behaviour rather than an aspiration.

## Related decisions

- ADR `0003` — DecentDB remains the store for this state.
- ADR `0008` — dual-layer rendering, preloading, and the no-black-frame transition rule are unchanged; this ADR changes only what plays next, not how a slide is drawn.
- ADR `0009` — `/display` and its playlist/progress endpoints stay public and outside the admin session boundary.
- ADR `0011` — quiet hours still pause and resume playback without touching cycle state.
- ADR `0007` — the incognito kiosk profile is the reason this state cannot live in the browser.
