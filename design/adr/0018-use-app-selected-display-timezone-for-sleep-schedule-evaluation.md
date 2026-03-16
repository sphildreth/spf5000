# ADR 0018: Use App-Selected Display Timezone for Sleep Schedule Evaluation

- Status: Accepted
- Date: 2026-03-16

## Context
ADR `0011` established app-managed quiet hours stored in DecentDB and enforced by `/display` using configured start and end times. That keeps scheduling inside the product instead of pushing it into `spf5000.toml`, Chromium flags, or OS schedulers, but the original decision assumed the Pi's local timezone was always the intended timezone for the frame.

That assumption breaks down when the administrator wants the frame to follow a different wall clock than the Pi host, or when the Pi timezone is left at a deployment default that does not match the intended display behavior. Administrators also need clearer UI feedback so they can tell whether quiet hours are following the Pi-local clock or an explicitly selected display timezone.

## Decision
This ADR refines ADR `0011` rather than replacing it. SPF5000 should continue to store the sleep schedule as app-managed settings with an enabled flag plus local start and end times, but quiet-hours evaluation should use an app-selected display timezone.

The display timezone is configured from the admin UI and stored in DecentDB-backed application settings. When no explicit display timezone is set, the system falls back to the Pi-local timezone. The configured display timezone and sleep schedule should flow through the display configuration so the public `/display` runtime can enforce quiet hours without requiring admin authentication.

The admin UI should expose the display timezone setting and show both the Pi-local clock and the configured display-time clock so administrators can understand which wall clock quiet hours will follow.

## Consequences
- Quiet hours remain app-managed and DecentDB-backed while becoming more predictable for frames whose intended display timezone differs from the Pi host timezone.
- Administrators can change sleep-schedule timezone behavior from the product UI instead of reconfiguring the OS timezone just to affect quiet hours.
- The display runtime and settings APIs must carry effective timezone information in addition to start and end wall-clock times.
- The admin UI becomes slightly more complex because it must explain the difference between Pi-local time and configured display time clearly.
