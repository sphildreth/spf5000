# ADR 0015: Use Alert Escalation and Visible Takeover Behavior on the Display

- Status: Accepted
- Date: 2026-03-16

## Context
Weather alerts change how `/display` behaves, not just what metadata is shown in the admin UI. SPF5000 already reserves a full-black fullscreen state for scheduled sleep (`0011`) and avoids intentional black frames during normal slide transitions (`0008`), so alert handling needs explicit presentation and precedence rules instead of ad hoc overlays.

The system also needs deterministic behavior when multiple alerts are active at the same time. A household appliance should show one dominant action at a time, while still letting the admin UI inspect all active alerts and cached provider state.

## Decision
Normalize alerts into SPF5000 alert models, map them to escalation modes (`ignore`, `badge`, `banner`, `fullscreen`, `fullscreen_repeat`), and resolve one dominant alert by effective escalation mode, severity, event priority, and newest timestamp.

On `/display`, the weather widget and non-fullscreen alert UI render as overlays that remain separate from the slideshow layers. Fullscreen alert takeover pauses slideshow timers without changing the dual-layer slideshow renderer, and `fullscreen_repeat` cycles back to a banner between repeated fullscreen episodes. Sleep mode remains the top precedence and does not wake for alerts by default.

## Consequences
- Alert behavior becomes deterministic, highly visible, and consistent with SPF5000's existing sleep and transition constraints.
- The admin UI can show both the dominant display action and the lower-priority active alerts without coupling alert policy into the NWS client itself.
- The display runtime gains additional state management for fullscreen alert episodes and precedence handling.
