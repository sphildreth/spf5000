# SPF5000 Follow-On Implementation Prompt
## Weather Provider + Weather Widget + Alert Takeover + Escalation Rules

You are working in the existing `spf5000` repository after the current in-flight work completes.

Your task is to implement the **complete first-pass weather and alert feature set** for SPF5000.

This includes:

1. weather provider abstraction
2. initial National Weather Service provider
3. corner weather widget on the display route
4. full-screen alert takeover behavior
5. alert escalation rules and prioritization
6. admin UI for configuration and visibility
7. DecentDB persistence and cached state
8. documentation and ADR/SPEC updates

This feature must integrate cleanly with the existing SPF5000 architecture:

- FastAPI backend
- React + TypeScript + Vite frontend
- DecentDB for settings/state
- browser-based fullscreen slideshow
- offline-first design philosophy
- no-flicker slideshow behavior
- app-managed sleep schedule
- existing display state model

---

## Product Goal

SPF5000 should become both:

- a digital picture frame
- an ambient weather and weather-alert display

Normal behavior:
- slideshow runs normally
- a compact weather widget appears in a configured corner
- weather data is refreshed periodically and served from local cached state

Alert behavior:
- active weather alerts are normalized and assigned escalation rules
- some alerts show as badge/banner only
- some alerts interrupt the slideshow with a full-screen alert takeover
- the most important active alert wins
- critical alerts can repeat periodically while still active

This feature should feel like a polished appliance, not a bolt-on gimmick.

---

## High-Level Scope

Implement all of the following as one cohesive slice:

### Backend
- weather provider abstraction
- `NWSWeatherProvider`
- weather current-conditions fetch
- active alerts fetch
- normalized weather model
- normalized alert model
- cached provider state
- alert escalation rule resolution
- background refresh/sync
- backend API for display and admin

### Frontend display
- corner weather widget
- alerting display states
- banner/fullscreen presentation behavior
- integration with slideshow without flicker
- widget hidden during sleep and full-screen alert takeover

### Frontend admin
- weather settings
- provider config
- active alert visibility
- provider/sync status
- alert escalation visibility

### Persistence
- DecentDB storage for settings, cached weather state, active normalized alerts, provider status, sync state

### Documentation
- README
- design docs
- ADRs
- user docs if appropriate

---

## Architectural Requirements

## 1. Provider abstraction

Implement a weather provider abstraction so additional global providers can be added later.

Suggested interface:

```text
WeatherProvider
  get_current_conditions(location)
  get_active_alerts(location)
  health_check()
```

The display route must never call external weather APIs directly.

All weather data must flow through:
- backend provider/service layer
- local cached state
- backend API
- display UI

The implementation must make it feasible to add future providers such as:
- Open-Meteo
- OpenWeatherMap
- Environment Canada
- UK Met Office

Do not special-case everything around NWS in a way that makes future providers awkward.

---

## 2. Initial provider: NWSWeatherProvider

Implement the first provider using the **US National Weather Service API**.

Use NWS for:
- current conditions / forecast-derived current display data
- active alerts

Requirements:
- no API key required
- location support appropriate for U.S. use
- normalize provider-specific payloads into SPF5000 models
- cache results locally
- survive transient provider failures cleanly

A provider-specific module structure such as the following is encouraged:

```text
backend/app/weather/
  providers/
    base.py
    nws.py
  services/
  repositories/
  models/
```

Integrate with existing repo structure if it differs.

---

## 3. Offline-first cache behavior

This feature must follow the project’s offline-first philosophy.

Requirements:
- backend fetches weather/alert data periodically
- results are cached in local application state/storage
- display consumes cached data from backend API
- if NWS is temporarily unavailable, SPF5000 continues functioning
- weather widget uses last known good data
- slideshow and display logic never depend on live remote calls during rendering

Do not build a design where the display route stalls waiting on NWS responses.

---

## 4. Weather widget requirements

Implement a corner weather widget for the `/display` route.

### Visual requirement
It should closely match the intended clean dashboard style already discussed:
- compact
- dark semi-transparent background
- weather icon on left
- large temperature text
- right-side details for precipitation, humidity, wind
- only one temperature unit shown at a time
- configurable °F or °C
- no simultaneous `°F | °C` presentation

### Functional requirements
- optional / enabled by setting
- configurable corner position
- hidden during sleep mode
- hidden during full-screen alert takeover
- non-interactive
- must not disturb slideshow transitions
- updated from backend cached weather data

### Suggested settings
Store in DecentDB:
- `weather_enabled`
- `weather_provider`
- `weather_location`
- `weather_units`
- `weather_position`
- `weather_refresh_minutes`
- `weather_show_precipitation`
- `weather_show_humidity`
- `weather_show_wind`

Keep the UI and implementation simple.

---

## 5. Alert model and normalization

Implement a normalized alert model independent of the raw NWS payload shape.

Suggested normalized structure:

```json
{
  "event": "Tornado Warning",
  "severity": "Extreme",
  "headline": "Tornado Warning for Johnson County",
  "description": "...",
  "instruction": "Take shelter immediately",
  "area": "Johnson County, KS",
  "issued": "...",
  "expires": "...",
  "escalation_mode": "fullscreen_repeat",
  "display_priority": 100
}
```

The provider/service layer should convert NWS alerts into this normalized model before the display/admin layers consume them.

---

## 6. Alert escalation rules

Implement alert escalation logic as a first-class feature.

Supported escalation modes:

- `ignore`
- `badge`
- `banner`
- `fullscreen`
- `fullscreen_repeat`

The system must assign an escalation mode to each normalized alert.

### Recommended default mapping
Use these defaults unless the existing design docs have been updated with equivalent logic:

#### fullscreen_repeat
- Tornado Warning
- Flash Flood Warning
- Civil Danger Warning
- Evacuation Immediate
- Shelter In Place Warning

#### fullscreen
- Severe Thunderstorm Warning
- Ice Storm Warning
- Blizzard Warning
- Dust Storm Warning
- Extreme Wind Warning

#### banner
- Tornado Watch
- Severe Thunderstorm Watch
- Flood Advisory
- Winter Weather Advisory
- Dense Fog Advisory
- Heat Advisory
- Wind Advisory

#### badge
- Flood Watch
- Freeze Watch
- Frost Advisory
- Special Weather Statement
- Hazardous Weather Outlook

#### ignore
- low-value informational/test messages as configured

The mapping should be implemented in a way that can be evolved later.

---

## 7. Alert priority resolution

When multiple alerts are active, SPF5000 must choose the correct visible action.

Implement deterministic conflict resolution:

1. higher escalation mode wins
2. if equal, higher severity wins
3. if equal, event-type priority map wins
4. if equal, newest active alert wins

You may implement this as a scoring model if clearer.

The result should be one dominant display action at a time for the fullscreen route, while lower-priority alerts may still appear in admin UI/history.

---

## 8. Full-screen alert takeover

Implement a full-screen alert presentation mode for high-priority alerts.

### Visual requirements
The screen must be highly visible from across the room.

Use a vivid high-contrast design with a strong:
- red
- yellow
- black
- white

Recommended style:
- black base
- red header bar
- yellow warning band / emphasis area
- large headline text
- short readable location line
- instruction text
- NWS attribution / issue-expiry info in smaller text

The design should feel closer to a broadcast emergency display than a normal app dialog.

### Functional requirements
- slideshow pauses while full-screen alert is active
- no slideshow transition flicker during takeover
- alert clears automatically when expired or otherwise inactive
- slideshow resumes automatically after alert clears
- no raw wall-of-text by default
- prioritize readability over completeness

Suggested text hierarchy:
- WEATHER ALERT
- event name
- area
- key instruction
- issued/expires info

---

## 9. Banner and badge modes

Implement lighter display modes for lower-priority alerts.

### badge
- small alert chip or indicator
- does not interrupt slideshow
- compact and attention-getting

### banner
- top or bottom horizontal band
- slideshow remains visible behind/around it
- event name clearly readable
- optional brief instruction snippet

These modes must integrate cleanly with the display route without destabilizing image transitions.

---

## 10. Fullscreen repeat behavior

Implement repeat behavior for `fullscreen_repeat` alerts.

Requirements:
- show alert full-screen for a configured duration
- return to slideshow
- re-show the alert after a configured interval while still active

Suggested settings:
- `weather_alert_repeat_enabled`
- `weather_alert_repeat_interval_minutes`
- `weather_alert_repeat_display_seconds`

Reasonable defaults:
- enabled: true
- interval: 5 minutes
- display duration: 20 seconds

This is especially important for Tornado Warning and other high-urgency alerts.

---

## 11. Display state model

Extend the display state model to support weather alert presentation.

A practical state model may include:

- `booting`
- `loading`
- `displaying`
- `sleeping`
- `empty`
- `alerting_banner`
- `alerting_fullscreen`

If you keep internal state slightly simpler, the resulting display behavior must still clearly distinguish:
- normal slideshow
- banner alert mode
- full-screen alert mode
- sleep mode

### State precedence
For v1, use this default precedence:
1. sleeping
2. alerting_fullscreen
3. alerting_banner
4. displaying
5. loading
6. empty

Document the chosen precedence clearly.

---

## 12. Sleep interaction

For v1, keep the default rule:

- sleep mode wins

That means:
- during the configured sleep window, the display remains black
- weather data and alerts may still be fetched/cached
- alert state is visible in admin/status
- alerts do not wake the display by default

Do not implement automatic sleep override unless it already exists as an established requirement.
You may leave room for a future setting like:
- `weather_alert_override_sleep_for_extreme`

but it is not required for this slice.

---

## 13. Admin UI requirements

Add a weather/alerts configuration area in the admin UI.

At minimum support:
- enable/disable weather
- provider selection (for now likely only NWS, but UI should not assume that forever)
- configure location
- choose units (F/C)
- choose widget position
- enable/disable alerts
- enable/disable full-screen takeover
- set minimum alert severity threshold
- configure repeat interval/display duration

Also show useful status:
- provider health
- last weather refresh
- last alert refresh
- active alerts list
- escalation mode being applied
- current display action
- recent sync/error state

Keep it clean and simple, not dashboard-bloated.

---

## 14. Location model

Implement a location configuration model suitable for NWS.

It is acceptable to start with a practical U.S.-focused representation such as:
- latitude/longitude
- zip code resolved to lat/lon
- city/state resolved to lat/lon via a documented helper path

Choose a clean implementation and document it.

The provider abstraction should not assume all future providers use the exact same raw location representation internally.

---

## 15. Backend API

Add backend API endpoints for display and admin use.

Suggested display endpoints:
- `GET /api/display/weather`
- `GET /api/display/alerts`

Suggested admin endpoints:
- `GET /api/admin/weather/settings`
- `PUT /api/admin/weather/settings`
- `GET /api/admin/weather/status`
- `GET /api/admin/weather/alerts`
- `POST /api/admin/weather/refresh`

You may adapt naming if the project already has an established admin settings route pattern.

Requirements:
- admin endpoints protected by admin auth
- display endpoints return cached normalized data
- useful validation and error messages
- no direct remote dependency in request flow beyond cached service logic

---

## 16. Background refresh strategy

Implement background refresh of weather and alerts.

Suggested default cadence:
- current weather: every 15 minutes
- alerts: every 2 minutes

Requirements:
- refresh work must not block slideshow rendering
- failures should be logged and surfaced in admin status
- last known good data should remain usable
- manual refresh trigger from admin UI should be supported

Use the project’s current background task/service approach where possible.

---

## 17. DecentDB persistence

Persist weather-related application settings and state in DecentDB.

At minimum persist:
- weather settings
- provider status
- last successful refresh times
- active normalized alerts
- cached current weather data
- escalation-related state if needed
- repeat-timing state if needed

Do not store giant raw payload archives unless clearly justified.
Normalize and store what is useful.

---

## 18. Testing

Add useful tests for:
- provider normalization
- weather unit handling
- alert escalation mapping
- alert priority/conflict resolution
- repeat behavior logic
- display-state precedence involving weather alerts
- repository persistence behavior
- API validation for weather settings

Use mocks/fakes for provider responses where practical.

The implementation should be structured to make deterministic tests possible.

---

## 19. Documentation updates

Update the following documentation:

- `README.md`
- `design/PRD.md`
- `design/SPEC.md`
- `design/ARD.md`

Also update/add relevant user docs under `docs/` if appropriate.

Add or update ADRs for:
1. weather provider abstraction
2. NWS as the initial provider
3. offline-first cached weather/alert model
4. full-screen alert takeover behavior
5. alert escalation and priority resolution

Keep ADRs concise and decision-oriented.

---

## 20. Constraints / Non-Goals

Do not:
- make the display route depend on live NWS responses
- overcomplicate the first UI
- build a universal weather framework beyond what is needed for clean provider abstraction
- weaken existing slideshow smoothness/no-flicker goals
- implement sound alarms in this slice unless already established elsewhere
- add weekday-based alert schedules or complex user-level personalization

Keep this implementation:
- robust
- readable
- appliance-friendly
- easy to extend later

---

## 21. Acceptance Criteria

This slice is complete when:

- weather provider abstraction exists
- `NWSWeatherProvider` works
- weather widget appears on the display route
- widget matches the intended compact overlay style
- alerts are normalized and assigned escalation modes
- badge/banner/fullscreen behaviors exist
- critical alerts can repeat in fullscreen mode
- full-screen alert display is highly visible from across the room
- alert priority/conflict resolution is deterministic
- admin can configure weather/alert settings
- all relevant state is persisted in DecentDB
- display continues working from cached state if NWS is unavailable
- docs and ADR/SPEC updates are complete

---

## 22. Implementation Notes

This should feel like a thoughtful household appliance feature.

The weather widget should feel calm and useful.
The alert system should feel serious and attention-grabbing when needed.
The slideshow must remain stable and polished throughout.

Favor:
- clarity
- determinism
- local caching
- strong state modeling
- readable code
- extensibility

Avoid:
- rushed direct-API hacks
- sloppy alert handling
- visually timid full-screen warnings
- making everything weather-specific in the general slideshow layer

Build the simplest good cohesive first version.
