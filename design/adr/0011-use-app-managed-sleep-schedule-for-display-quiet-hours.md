# ADR 0011: Use App-Managed Sleep Schedule for Display Quiet Hours

- Status: Accepted
- Date: 2026-03-15

## Context
ADR 0003 keeps application settings in DecentDB, ADR 0007 keeps the Raspberry Pi runtime centered on a continuously running browser kiosk session, ADR 0008 keeps normal image-to-image transitions free of intentional black frames, and ADR 0009 limits `spf5000.toml` to startup/runtime concerns. The new sleep schedule feature adds quiet-hours behavior that changes how `/display` behaves over time, so it needs an explicit architectural decision instead of ad hoc documentation.

Several implementation options exist: put sleep hours in `spf5000.toml`, use OS-level shutdown or monitor blanking, wire cron or `systemd` timers around Chromium, or keep the feature inside the application. The chosen approach needs to stay editable from the admin UI, survive restarts, preserve the appliance feel, and let the display enter and leave sleep mode without reboot choreography or special browser flags.

## Decision
Store the sleep schedule in DecentDB-backed application settings using an enabled flag plus local start and end times. Expose the schedule through authenticated admin APIs and the admin UI, and include the effective schedule in the display playlist/config flow so the `/display` runtime can enforce it directly.

When the current device-local time falls inside the configured sleep window, `/display` renders a solid black fullscreen sleep state and pauses slideshow advancement and transitions. The sleep window uses local device time, the start time is inclusive, the end time is exclusive, and playback resumes automatically when the window ends. When the schedule is enabled, identical start and end times are rejected as invalid. This full-black state is reserved for scheduled sleep mode only and does not change ADR 0008's rule that normal slide-to-slide transitions must not intentionally show a black frame.

`spf5000.toml`, Chromium kiosk flags, cron jobs, and `systemd` timers remain out of scope for quiet-hours scheduling.

## Consequences
- Quiet-hours behavior stays consistent with the existing DecentDB settings model and remains editable from the admin UI without SSH or OS reconfiguration.
- The Pi appliance can stay powered on with the backend and Chromium running while the application itself decides when the display should appear asleep.
- The display runtime becomes responsible for time-window evaluation, pause/resume behavior, and sleep-state rendering rather than delegating that logic to the OS.
- Operators must keep device-local time correct because the schedule intentionally follows the frame's local clock, including overnight windows and wake-at-end-time behavior.
