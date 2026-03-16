# ADR 0013: Use Provider Abstraction and Cached State for Weather and Alerts

- Status: Accepted
- Date: 2026-03-16

## Context
SPF5000 is intentionally offline-first at display time. Accepted ADRs already keep structured state in DecentDB (`0003`), keep external integrations behind provider boundaries (`0005`), and keep `/display` dedicated to locally controlled presentation behavior (`0008`, `0011`, `0012`).

Adding weather and severe-weather alerts introduces a new category of external data that changes both the admin UI and the public display surface. The implementation needs to support future providers, keep the display route independent from live remote calls, and preserve useful cached state when the network or upstream provider is unavailable.

## Decision
Implement weather and alert support as a dedicated backend subsystem with its own weather-provider abstraction, normalization layer, cached state model, and scheduled refresh workflow.

Weather preferences remain in the existing DecentDB-backed `settings` table, while cached provider state, current conditions, active normalized alerts, and refresh history live in dedicated weather tables. The display surface consumes only cached data exposed through backend APIs such as `/api/display/weather` and `/api/display/alerts`; it never calls an upstream weather provider directly.

## Consequences
- SPF5000 can add future weather providers without reworking the display or admin layers around provider-specific payloads.
- The display route preserves the offline-first model because weather and alerts render from local cached state instead of live provider calls.
- The backend gains more orchestration, persistence, and refresh logic to manage alongside photo-source providers.
