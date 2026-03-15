# SPF5000 Follow-On Implementation Prompt
## Boot / Loading / Empty-State Display Experience

You are working in the existing `spf5000` repository after the current in-flight work completes.

Your task is to implement a polished **boot/loading/ready state experience** for the fullscreen display route.

The goal is to make SPF5000 feel like a real appliance during startup, sync warmup, and “no photos yet” conditions, instead of feeling like a browser page waiting on data.

This work applies to the fullscreen display experience only. It should not introduce admin UI clutter into the display route.

---

## Goals

Implement the following:

1. A dedicated **boot/loading screen** for the display route
2. A clean **display state model** for fullscreen runtime states
3. A tasteful **empty-state screen** when no playable photos are available
4. A smooth transition from loading to slideshow playback
5. Documentation and ADR/SPEC updates

---

## Desired User Experience

When the Pi boots and Chromium opens `/display`, the viewer should see an intentional SPF5000 startup experience rather than a blank or half-rendered page.

The desired behavior is:

- Chromium opens fullscreen to `/display`
- SPF5000 initially shows a branded loading/boot screen
- the loading screen remains visible while:
  - backend data is loading
  - playlist is being prepared
  - cached assets are not yet ready
  - providers are warming up or syncing
- once the slideshow is ready, the app transitions cleanly into the first image
- if there are no usable photos, an intentional empty-state screen is shown
- the sleep schedule still uses a pure black screen and remains visually distinct from boot/loading

---

## Architectural Requirements

### Display state model

Introduce an explicit display-state model for the fullscreen display route.

At minimum support these states:

- `booting`
- `loading`
- `displaying`
- `sleeping`
- `empty`

You may collapse `booting` and `loading` internally if needed, but the resulting UI behavior must still feel intentional and polished.

### State meanings

#### booting
Initial startup state while the display app is establishing readiness.

#### loading
The system is active, but slideshow playback is not yet ready because playlist/assets/state are still being prepared.

#### displaying
Normal slideshow playback state.

#### sleeping
Scheduled sleep period. This must remain a **pure black screen** with no branding or loading text.

#### empty
No usable photos are currently available for display.

---

## 1. Boot / loading screen

Implement a fullscreen branded loading experience for the display route.

Requirements:
- fullscreen
- dark/black background or otherwise tasteful minimal background
- prominent **SPF5000** branding/title
- short status text such as:
  - `Starting slideshow...`
  - `Loading photos...`
  - `Preparing display...`
- optional subtle animation such as:
  - spinner
  - pulsing dots
  - simple motion accent
- no browser chrome
- no debug text by default
- no technical jargon visible to normal users

This should feel like:
- appliance startup
- not a developer waiting page
- not a generic blank React shell

### Important rule
The loading screen must be **state-driven**, not a fake fixed delay.

Do **not** intentionally show it for a hardcoded minimum time unless there is a very small UX-motivated threshold and it is justified.

The loading screen should disappear as soon as the slideshow is genuinely ready.

---

## 2. Empty-state screen

Implement a dedicated fullscreen empty-state when no playable photos are available.

Requirements:
- fullscreen
- tasteful visual consistency with the loading screen
- clear but simple message, such as:
  - `No photos available yet`
  - `Add photos to start the slideshow`
- no scary error styling
- no stack traces
- no raw API error content

This state should be used when:
- the local library is empty
- all configured sources are unavailable and no cached playable images exist
- the current playlist resolves to zero usable items

This should be distinct from:
- loading
- sleeping
- slideshow playback

---

## 3. Readiness model

The display UI should not start slideshow transitions until the system is genuinely ready.

Define a clear readiness contract between backend and display UI.

A reasonable implementation may include:
- a display status endpoint
- playlist readiness metadata
- asset availability checks
- a frontend readiness state machine

Suggested ideas:
- `GET /api/display/status`
- `GET /api/display/playlist`

Display readiness should consider:
- whether there are playable assets
- whether the playlist is loaded
- whether the next asset can be rendered
- whether the system is in scheduled sleep mode

Do not transition into slideshow playback until readiness is satisfied.

---

## 4. Transition from loading to slideshow

Once the slideshow is ready:
- transition cleanly from loading state to the first image
- avoid a hard white flash or browser repaint feeling
- avoid exposing a black intermediary frame unless intentionally part of the transition
- preserve the project’s no-flicker design principles

A subtle fade or clean slide into the first image is acceptable.

### Important distinction
The rule “no full black screen between slideshow images” still applies during normal playback.

However:
- **sleeping** intentionally uses a black screen
- **boot/loading** intentionally uses a branded loading screen
- **empty** intentionally uses an empty-state screen

---

## 5. Interaction with sleep schedule

The existing sleep schedule behavior remains valid and must continue to work.

Requirements:
- if the current time is inside the sleep window, display must show the **sleeping** state, not the loading screen
- sleep state must remain visually distinct:
  - pure black
  - no logo
  - no spinner
  - no “loading” text

State precedence should be designed intentionally. A reasonable approach is:

1. sleeping
2. displaying
3. loading/booting
4. empty

Or similar, so long as the behavior is deterministic and well documented.

Choose a clear precedence model and document it.

---

## 6. Frontend implementation expectations

Update the display-side React implementation to include:
- display state handling
- dedicated components/screens for loading and empty states
- clean state transitions
- minimal but polished styling

Keep it simple and maintainable.

Do not pull in a heavy UI framework just for this.
Prefer:
- existing project styling approach
- plain CSS / CSS modules / lightweight styling already in use

The display route should remain highly focused and not depend on the admin shell.

---

## 7. Backend support

Add any backend support required to make the display state model robust.

Potential backend responsibilities:
- return display readiness/status
- return whether the system is in sleep mode
- return whether playlist/assets are available
- distinguish empty library from still-loading state

Use the existing backend architecture cleanly.
Do not overcomplicate this if the frontend can derive most of the state safely.

---

## 8. Testing

Add tests for the readiness/display-state logic where practical.

Priority areas:
- loading vs empty behavior
- sleep-state precedence
- transition into displaying when assets become available
- no accidental fallback to blank/undefined page state

Use reasonable backend/domain tests and frontend component/state tests if the repo supports them.

---

## 9. Documentation updates

Update documentation to reflect the display boot/ready-state behavior.

At minimum update:
- `README.md`
- `design/PRD.md`
- `design/SPEC.md`
- `design/ARD.md`

Update or add ADRs to reflect:
- fullscreen display uses explicit runtime state handling
- boot/loading/empty states are intentional appliance UX
- sleep state remains a separate black-screen mode

Keep ADRs concise and decision-oriented.

---

## 10. Constraints / Non-Goals

Do not implement:
- complicated progress bars requiring real provider percentage tracking
- noisy debug overlays on the display screen
- a separate installer splash executable
- arbitrary “branding system” complexity
- admin controls embedded directly in the display route

Keep this feature:
- polished
- minimal
- appliance-like
- resilient

---

## 11. Acceptance Criteria

This work is complete when:

- `/display` shows a polished loading/boot screen while slideshow playback is not ready
- `/display` shows a dedicated empty-state when no playable photos are available
- `/display` transitions cleanly into slideshow playback once ready
- sleep schedule still renders a pure black screen
- display states are explicit and maintainable
- docs and ADR/SPEC updates are complete

---

## 12. Implementation Notes

This feature exists to improve first impression and appliance feel.

The user should never feel like they are staring at:
- a blank browser page
- a half-rendered React app
- a confusing loading failure

The loading screen should feel intentional.
The empty state should feel calm.
The slideshow transition should feel smooth.

Build the simplest good version.
