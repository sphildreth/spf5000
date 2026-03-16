# SPF5000 Follow-On Implementation Prompt
## Sleep Schedule Support (DB + Admin UI + Display Enforcement)

You are working in the existing `spf5000` repository after the current in-flight work completes.

Your task is to implement **daily sleep schedule support** for SPF5000.

This feature must be implemented as an **application-level behavior**, not an operating system shutdown/suspend feature.

The Raspberry Pi, backend service, and kiosk browser should remain running. During the configured sleep window, the display should render a **solid black fullscreen screen** and stop slideshow advancement. When the sleep window ends, the slideshow should resume automatically.

---

## Goals

Implement the following:

1. Sleep schedule settings stored in **DecentDB**
2. Sleep schedule editable in the **admin UI**
3. Sleep schedule accessible via backend API
4. Sleep schedule enforced by the **display route / slideshow runtime**
5. Documentation and ADR/SPEC updates

---

## Architectural Requirements

### Source of truth
Sleep schedule is an **application setting** and must be stored in **DecentDB**.

It must **not** be stored in:
- `spf5000.toml`
- systemd unit files
- cron
- OS power management settings
- Chromium startup flags

`spf5000.toml` remains only for runtime/startup configuration, not user-editable application behavior.

### Enforcement model
The sleep schedule must be enforced by the SPF5000 application itself.

During the configured sleep window:
- slideshow advancement stops
- slideshow transitions stop
- display renders a full black screen
- browser stays open
- backend stays running
- Pi stays powered on

Outside the configured sleep window:
- slideshow runs normally
- playback resumes automatically without restart

---

## Required Features

## 1. Settings model

Add support for these settings:

- `sleep_schedule_enabled` (boolean)
- `sleep_start_local_time` (string in `HH:MM` 24-hour format)
- `sleep_end_local_time` (string in `HH:MM` 24-hour format)

Suggested initial defaults:

- enabled: `false`
- start: `22:00`
- end: `08:00`

These values may live in a general settings store or a dedicated display/settings repository, but they must be persisted in DecentDB.

### Validation requirements
Validate:
- time format is valid 24-hour `HH:MM`
- values are normalized consistently
- overnight windows are supported, e.g. `22:00` to `08:00`
- same-time edge cases are handled intentionally

Document how same-time values are interpreted. A reasonable default is:
- if start == end and enabled == true, treat as “always awake” or reject validation explicitly
- choose one behavior and document it clearly

---

## 2. Backend API

Add backend API support for reading and updating sleep schedule settings.

Suggested route shape:

- `GET /api/admin/settings/sleep-schedule`
- `PUT /api/admin/settings/sleep-schedule`

Requirements:
- protected by admin auth
- returns current values
- validates updates
- persists updates in DecentDB
- returns useful error messages on invalid input

You may adapt the route naming if there is already an established settings API pattern in the repo.

---

## 3. Admin UI

Add an admin UI section/page/control for sleep schedule management.

Requirements:
- editable from the admin interface
- includes:
  - enable/disable toggle
  - start time field
  - end time field
- clear labeling
- basic validation feedback
- save action persists settings through the backend API
- existing values load when opening the page

This does not need a giant settings experience. Keep it simple and clean.

If the admin UI already has a Settings page, integrate there.
If not, add a minimal Display Settings or Sleep Schedule section.

---

## 4. Display runtime behavior

Update the fullscreen display logic so it evaluates whether the current local time is inside the configured sleep window.

### During sleep window
Display behavior must be:
- solid black fullscreen screen
- no slideshow movement
- no image transitions
- no placeholder text by default
- no visible browser chrome
- no flicker

### Outside sleep window
Display behavior must:
- resume slideshow automatically
- continue from current/next image in a reasonable way
- not require page reload or service restart

### Transition behavior
If sleep begins while an image is currently displayed:
- transition cleanly into black state
- do not flash a full black frame between ordinary slideshow images outside scheduled sleep
- keep the no-flicker principles intact

The black sleep screen is intentional during the scheduled sleep window.
The no-black-frame rule still applies to normal image-to-image slideshow transitions.

---

## 5. Time handling

Treat the schedule as **local device time**.

Requirements:
- compare against the Pi’s local time
- support overnight windows such as `22:00` to `08:00`
- keep the implementation understandable

A helper/service function for schedule evaluation is recommended, for example:

```text
is_within_sleep_window(now_local_time, enabled, start_time, end_time) -> bool
```

This logic should be covered by tests.

---

## 6. Testing

Add tests for sleep schedule evaluation logic.

Test cases should include at least:
- disabled schedule
- simple same-day window
- overnight window
- boundary times
- invalid time input handling
- documented same-time behavior

If frontend tests exist, add a small amount of coverage for settings form behavior where practical.
If not, backend/domain tests are the priority.

---

## 7. Documentation updates

Update the relevant documentation to make this a clearly documented v1 behavior.

At minimum update:
- `README.md`
- `design/PRD.md`
- `design/SPEC.md`
- `design/ARD.md`

Update or add ADRs to reflect:
- sleep schedule is app-managed, not OS-managed
- sleep schedule is stored in DecentDB and editable in admin UI

Also ensure the Pi setup guide remains consistent with this behavior:
- sleep schedule handled by SPF5000
- not by shutting down the Pi or browser

---

## 8. Constraints / Non-Goals

Do not implement:
- OS suspend/shutdown scheduling
- monitor power-off scheduling
- cron-based blanking
- advanced calendar scheduling
- weekday-specific schedules
- multiple schedule profiles
- text overlays like “sleeping” unless already established and explicitly desired

Keep v1 to:
- one daily enabled/disabled schedule
- one start time
- one end time
- black screen during sleep

---

## 9. Acceptance Criteria

This work is complete when:

- sleep schedule settings are persisted in DecentDB
- sleep schedule is editable in the admin UI
- backend API exposes current schedule and accepts updates
- display route enforces black-screen sleep mode during schedule window
- slideshow resumes automatically outside the window
- overnight schedules work correctly
- logic is tested
- documentation and ADR/SPEC updates are complete

---

## 10. Implementation Notes

Keep this modest and robust.

This feature exists to support appliance-like family use:
- the frame stays on
- the screen goes black at night
- it wakes itself in the morning

Favor:
- clarity
- predictable behavior
- simple admin UX
- local time semantics
- explicit tests

Avoid:
- overengineering
- OS-level complexity
- hidden magic

Build the simplest good version.
