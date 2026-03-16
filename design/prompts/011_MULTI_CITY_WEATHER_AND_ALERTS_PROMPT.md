# SPF5000 Follow-On Implementation Prompt
## Multi-City Weather Rotation + Per-Location Alerts + Location-Aware Alert Prioritization

You are working in the existing `spf5000` repository after the current in-flight work completes.

Your task is to evolve the weather system from a **single-location weather widget** into a **multi-location weather card rotator** with **per-location alert settings** and **location-aware alert prioritization**.

This feature must integrate cleanly with the current SPF5000 architecture and the planned theme system.

---

## Product Goal

SPF5000 should support multiple configured weather locations at the same time.

The user experience goal is:

1. The display shows a compact weather card in a configured corner.
2. The card rotates through multiple active configured locations.
3. Rotation uses a smooth vertical "flip/reveal" style transition.
4. One location can be marked as **home** and gets a special visual accent.
5. Each location can independently enable or disable:
   - weather display
   - alert monitoring
   - alert takeover behavior
6. If alerts are active in multiple watched locations, SPF5000 chooses the correct visible alert based on:
   - escalation mode
   - severity
   - location priority
   - recency
7. Full-screen alert messaging must identify **which watched location** is affected, such as:
   - `HOME — Kansas City, MO`
   - `MOM — Springfield, MO`

This should feel like a polished family-oriented weather and safety feature.

---

## High-Level Scope

Implement all of the following:

### Backend
- evolve weather settings/storage from single-location to multi-location
- support CRUD for watched weather locations
- per-location settings for weather display and alerts
- per-location cached weather data
- per-location cached alert state
- location-aware alert normalization and prioritization

### Frontend display
- rotating weather card component
- vertical flip/reveal transition between cities
- home location accent styling hook
- card rotation timing control
- location-aware alert display text

### Frontend admin
- add/manage/edit weather locations
- active toggle
- home toggle
- weather enabled toggle
- alerts enabled toggle
- alert takeover toggle
- location priority/order
- rotation settings

### Persistence
- DecentDB schema changes for multi-location weather
- per-location weather/alert settings and state

### Documentation
- update README
- update design docs
- update ADRs/SPEC/PRD as needed
- keep the theme integration story coherent

---

## Architectural Requirements

## 1. Multi-location weather model

Weather must no longer be modeled as one global location.

Instead, use:

### Global weather settings
Applies to the weather feature overall, such as:
- provider
- widget position
- units
- rotation enabled
- rotation seconds
- transition style
- display field toggles (precipitation, humidity, wind)

### Per-location weather entries
Each watched location is a first-class record.

Each location should support at minimum:

- `id`
- `name`
- `location_type`
- `query_value` or equivalent location definition
- `latitude`
- `longitude`
- `is_active`
- `is_home`
- `priority_order`
- `weather_enabled`
- `alerts_enabled`
- `alert_takeover_enabled`
- `alert_min_severity`
- `accent_style` (optional but strongly recommended for theme integration)
- `sort_order`

If the provider/location model requires a slightly different representation, keep the same intent.

---

## 2. Rotation model

The weather overlay becomes a **single card rotator** rather than multiple simultaneous cards.

### Required behavior
- one card visible at a time
- rotate through active weather-enabled locations
- if only one eligible location exists, no rotation occurs
- if zero eligible locations exist, widget is hidden or omitted gracefully
- if a location has no valid cached weather, skip it until data becomes available

### Rotation configuration
Global settings should include:

- `weather_rotation_enabled`
- `weather_rotation_seconds`
- `weather_transition_style`

For v1 of this enhancement, support:

- `vertical_flip`

Optional future styles:
- `fade`
- `slide_up`
- `cut`

But only `vertical_flip` is required now.

---

## 3. Vertical flip / reveal transition

The desired visual effect is:

> a new card slowly appears from top to bottom, covering the one underneath

This should be implemented as a smooth card transition, not a crude hard cut.

Requirements:
- smooth and readable
- no flicker
- no layout jump
- no slideshow stutter
- weather card remains compact and stable in its corner

A practical implementation may use:
- two stacked card layers
- one entering layer
- one exiting/background layer
- controlled transform/clip/opacity transition

The effect should feel like a rotating information card, not a page reload.

---

## 4. Home location treatment

One location may be marked as the **home** location.

Requirements:
- only one location may be home at a time
- the home location receives a distinctive accent
- the accent must integrate with the theme/context accent system

Examples of home treatment:
- house icon
- accent border
- glow
- gradient border
- rainbow gradient border

Do not hardcode one style into the component.
Home styling should consume theme/context styling plus per-location accent style if supported.

This is especially important because users may want playful or personal styling, such as a purple-forward rainbow gradient border.

---

## 5. Per-location alert controls

Each watched location must independently control whether alerts are monitored and how they behave.

Per-location alert-related fields should include:

- `alerts_enabled`
- `alert_takeover_enabled`
- `alert_min_severity`

Possible interpretation:
- `alerts_enabled = false` means the location is ignored for alert monitoring
- `alerts_enabled = true` and `alert_takeover_enabled = false` means alerts may appear in lower-impact modes or admin state, but not necessarily full-screen takeover
- `alert_takeover_enabled = true` allows this location’s alerts to compete for banner/fullscreen display according to escalation rules

This gives the user important flexibility, for example:
- show weather for a city but ignore its alerts
- monitor mom’s city for alerts even if it is not shown often in the weather rotation
- allow home and mom to interrupt, but not vacation house

---

## 6. Multi-location alert model

Alerts must now be location-aware.

A normalized alert must include at minimum:

- `location_id`
- `location_name`
- `is_home`
- `priority_order`
- `event`
- `severity`
- `headline`
- `description`
- `instruction`
- `issued`
- `expires`
- `escalation_mode`
- `display_priority`

Suggested normalized example:

```json
{
  "location_id": "mom-springfield",
  "location_name": "Mom",
  "is_home": false,
  "priority_order": 20,
  "event": "Tornado Warning",
  "severity": "Extreme",
  "headline": "Tornado Warning for Springfield",
  "instruction": "Take shelter immediately",
  "issued": "...",
  "expires": "...",
  "escalation_mode": "fullscreen_repeat",
  "display_priority": 100
}
```

This must support multiple active alerts across multiple locations at the same time.

---

## 7. Alert prioritization across multiple locations

The alert system must now choose the dominant visible alert from a set of active location-aware alerts.

Implement deterministic conflict resolution:

1. higher escalation mode wins
2. if equal, higher severity wins
3. if equal, higher location priority wins
4. if equal, newer alert wins

### Location priority
Use `priority_order` (or equivalent) as a location-priority input.

This allows families to care more about:
- home
- mom
- kids
- second home
- travel locations

You may choose whether lower number = higher priority or vice versa, but document it clearly and use it consistently.

### Home influence
`is_home` may also be factored into presentation or tie-breaking if helpful, but do not make the logic ambiguous.
Prefer explicit priority values over magical hidden priority.

---

## 8. Display behavior for alerts

When a fullscreen or banner alert is shown, it must identify the affected location clearly.

Examples:

- `HOME — Kansas City, MO`
- `MOM — Springfield, MO`
- `DENVER — Denver, CO`

If a location is marked home:
- show a home indicator or label
- preserve readability
- do not let cute styling weaken alert clarity

Full-screen alerts should remain highly legible from across the room.

Lower-priority badge/banner alerts should also show the location label so the household understands who/where is affected.

---

## 9. Admin UI requirements

Add a weather locations management UI.

Required capabilities:
- list watched locations
- add location
- edit location
- delete location
- toggle active
- toggle weather enabled
- toggle alerts enabled
- toggle alert takeover enabled
- mark one as home
- change priority order / sort order
- set display name
- configure location input
- optionally choose accent style

Suggested columns/fields:
- name
- location
- active
- weather
- alerts
- takeover
- home
- priority
- status / last update

Also add global weather rotation settings:
- rotation enabled
- rotation seconds
- transition style

Keep it simple and usable.

---

## 10. Theme integration requirements

This feature must be implemented in a way that respects the SPF5000 theme system.

Requirements:
- weather rotator card uses theme tokens
- home-city styling is a contextual accent, not hardcoded CSS
- per-location `accent_style` may override or refine the home treatment
- widget remains visually coherent across built-in and contributed themes

Examples of acceptable home accent styles:
- `default`
- `subtle_border`
- `house_icon`
- `gradient_border`
- `rainbow_gradient_border`

The feature should be ready for theme-aware treatment even if only a few accent styles are implemented immediately.

---

## 11. Backend API changes

Add or evolve backend endpoints to support multi-location weather.

Suggested endpoints:

### Display
- `GET /api/display/weather`

This should now return:
- global weather display config
- rotation settings
- active eligible location cards with cached weather data

### Admin
- `GET /api/admin/weather/settings`
- `PUT /api/admin/weather/settings`
- `GET /api/admin/weather/locations`
- `POST /api/admin/weather/locations`
- `PUT /api/admin/weather/locations/{id}`
- `DELETE /api/admin/weather/locations/{id}`
- `POST /api/admin/weather/refresh`

You may adapt route naming to match the existing admin API pattern.

Requirements:
- admin endpoints protected by auth
- display endpoint returns only what the display needs
- all responses use normalized data models
- useful validation errors for bad location input

---

## 12. Persistence requirements

Persist all multi-location weather configuration and state in DecentDB.

At minimum store:

### Global settings
- provider
- units
- widget position
- rotation enabled
- rotation seconds
- transition style
- field visibility toggles

### Per-location configuration
- name
- location definition
- active/home flags
- priority/sort
- weather/alert settings
- accent style

### Cached provider state
- current normalized weather per location
- active normalized alerts per location
- last successful refresh times
- provider health/status per location if needed

Do not regress the offline-first architecture.

---

## 13. Refresh and caching behavior

Weather and alerts should continue to use cached local state.

Requirements:
- refresh all active relevant locations in background
- cache each location’s weather data independently
- cache each location’s alert state independently
- if one location fails refresh, others continue working
- if one location has stale but still useful data, the display may continue using last known good values
- display rotator should skip completely unusable locations rather than break the widget

This feature must remain resilient.

---

## 14. Edge-case behavior

Implement and document sensible behavior for edge cases.

### If only one location is weather-enabled and active
- show the single card
- do not rotate

### If a location is alerts-enabled but weather-disabled
- it may still participate in alert monitoring
- it does not need to appear in the weather card rotation

### If home location is inactive
- it should not appear in rotation
- its alert behavior should follow its alert settings
- admin UI should still show that it is marked home, or require cleanup if your chosen model enforces stricter validity

### If multiple locations are marked home
- reject or auto-correct
- there must be only one effective home location

### If no active weather cards exist
- hide widget gracefully

### If multiple alerts tie closely
- use the documented prioritization rules deterministically

---

## 15. Testing

Add useful tests for:

- location CRUD validation
- single-home enforcement
- weather rotation eligibility logic
- skipped invalid/inactive/stale locations
- per-location alert enablement logic
- alert prioritization across multiple locations
- location-aware normalized alert models
- backend API validation
- transition style setting persistence

If frontend tests exist, add:
- weather rotator state behavior
- home accent rendering hook behavior
- rotation skipping invalid cards
- stable rendering during card change

Keep the code structured for deterministic testing.

---

## 16. Documentation updates

Update all relevant documentation.

At minimum update:
- `README.md`
- `design/PRD.md`
- `design/SPEC.md`
- `design/ARD.md`

Also update weather-related design docs and add/update ADRs for:
1. multi-location weather model
2. rotating single-card weather display
3. per-location alert enablement and takeover settings
4. location-aware alert prioritization

If user-facing docs exist under `docs/`, update them as well.

---

## 17. Constraints / Non-Goals

Do not:
- render multiple weather cards at once in different corners
- hardcode home styling in a way that fights the theme system
- let weather card transitions introduce display flicker
- weaken the alert readability model
- overcomplicate v1 with route planning or geofencing
- assume all locations are U.S.-only forever in the general model, even though the first provider may be NWS

Keep the model extensible but implement the simplest good version now.

---

## 18. Acceptance Criteria

This work is complete when:

- multiple watched weather locations are supported
- locations can be active/inactive independently
- one location can be marked home
- a single weather card rotates through eligible active locations
- rotation timing is configurable
- vertical flip/reveal transition exists
- home location gets special accent treatment
- per-location alert monitoring exists
- per-location alert takeover enablement exists
- alerts include watched-location identity in display output
- alert prioritization is deterministic across locations
- all relevant settings/state persist in DecentDB
- docs and ADR/SPEC updates are complete

---

## 19. Implementation Notes

Favor:
- strong state modeling
- deterministic prioritization
- resilient caching
- theme-aware styling
- simple admin UX
- clear location labeling in alerts

Avoid:
- global-only alert assumptions
- hardcoded one-off home styling hacks
- card rotation implementations that feel janky
- feature coupling that makes future weather providers awkward

Build the simplest good cohesive multi-location version.
