# SPF5000 Follow-On Implementation Prompt
## Health / Doctor Page

You are working in the existing `spf5000` repository after the current in-flight work completes.

Your task is to implement a **Health / Doctor Page** for SPF5000.

This feature should give admins a single place to verify that the frame is healthy, configured correctly, and able to perform its core responsibilities.

The page should be useful for:
- first-time setup validation
- troubleshooting
- confirming source/provider health
- confirming display/runtime readiness
- identifying degraded conditions before the user notices them

This feature must integrate cleanly with the existing SPF5000 architecture:

- FastAPI backend
- React + TypeScript + Vite frontend
- DecentDB for app settings/state
- admin-auth-protected UI
- provider-based architecture
- local cache/storage model
- Raspberry Pi appliance runtime

---

## Product Goal

SPF5000 should have a simple but useful **Doctor Page** that answers:

- Is the app up?
- Is the database healthy?
- Are image libraries/collections available?
- Are providers healthy?
- Is weather working?
- Are alerts working?
- Is the display likely able to operate correctly?
- Are there obvious problems such as missing config, empty collections, failing sync, or stale cached data?

This should feel like a practical operator/admin page, not an internal-only debug dump.

---

## Scope

Implement:

1. backend health-check aggregation service
2. health/doctor API endpoints
3. admin UI doctor page
4. provider/source health reporting
5. core system checks
6. status severity model
7. documentation and ADR/SPEC updates

Optional but encouraged:
- refresh button
- last-checked timestamp
- suggested remediation text
- lightweight “copy diagnostics summary” feature

---

## High-Level Requirements

## 1. Doctor page purpose

The doctor page should summarize the operational state of SPF5000 and surface:
- healthy
- warning
- error

for major subsystems.

It should not require the admin to inspect logs just to know whether the system is working.

---

## 2. Checks to include

At minimum, include checks for:

### Application
- backend reachable
- app version/build info if available
- current time / timezone if useful

### Database
- DecentDB file exists
- DecentDB connection succeeds
- simple query succeeds
- schema appears initialized

### Configuration
- runtime config present and readable
- required directories exist
- data directory writable
- cache directory writable

### Admin/Auth
- bootstrap complete / admin exists
- auth system initialized

### Media / Libraries / Collections
- at least one collection/library exists
- at least one playable image exists
- active slideshow pool is non-empty
- count of assets by status if practical

### Providers / Sources
For each configured provider:
- enabled/disabled
- healthy/unhealthy/degraded
- last successful sync
- last error if any
- configured but not connected state

This should include current source types such as:
- local files
- Google Photos if implemented
- future providers automatically if architecture allows

### Weather / Alerts
If weather feature exists:
- provider health
- location count
- last weather refresh
- last alert refresh
- active alert count
- stale weather data warning if relevant

### Display Runtime
- display route readiness state if known
- active sleep schedule state
- current display mode if available
- active alert takeover state if available

### Backup / Restore
If implemented:
- database backup capability available
- export paths writable
- recent backup/export errors if tracked

---

## 3. Severity model

Each check must produce a normalized result:

- `ok`
- `warning`
- `error`
- optionally `info`

Each result should include:
- id
- title
- severity
- summary
- optional details
- optional remediation hint

Suggested shape:

```json
{
  "id": "database_connection",
  "title": "Database Connection",
  "severity": "ok",
  "summary": "DecentDB opened successfully.",
  "details": "Simple query completed.",
  "remediation": null
}
```

This makes the doctor page easy to render and extend.

---

## 4. Aggregation model

Implement a health aggregation service that combines checks from multiple subsystems.

Suggested structure:

- `DoctorService`
- subsystem checkers such as:
  - `ApplicationDoctorChecks`
  - `DatabaseDoctorChecks`
  - `StorageDoctorChecks`
  - `ProviderDoctorChecks`
  - `DisplayDoctorChecks`
  - `WeatherDoctorChecks`

If the existing codebase prefers a different structure, keep the same intent:
- modular checks
- composable results
- easy to extend

---

## 5. Backend API

Add doctor endpoints.

Suggested routes:

- `GET /api/admin/doctor`
- `POST /api/admin/doctor/refresh` (optional if explicit refresh behavior is useful)

Requirements:
- admin-auth protected
- response contains:
  - overall status
  - check groups
  - individual checks
  - timestamp
- clear and stable shape
- no raw stack traces in normal responses

Suggested response shape:

```json
{
  "overall_status": "warning",
  "checked_at": "2026-03-18T20:15:00Z",
  "groups": [
    {
      "id": "database",
      "title": "Database",
      "status": "ok",
      "checks": [...]
    },
    {
      "id": "providers",
      "title": "Providers",
      "status": "warning",
      "checks": [...]
    }
  ]
}
```

---

## 6. Admin UI requirements

Add a dedicated Doctor page in the admin UI.

The page should:
- show grouped subsystem health cards/sections
- make overall system health obvious
- use color/status indicators
- show short human-readable summaries
- allow refresh/recheck
- surface remediation hints where helpful

Suggested sections:
- Overall Status
- Application
- Database
- Storage / Paths
- Media / Collections
- Providers / Sources
- Weather / Alerts
- Display Runtime
- Backup / Export

Keep the UI calm and useful, not noisy.

---

## 7. User experience goals

The doctor page should help an admin quickly answer:

- Why isn’t anything showing?
- Why is weather missing?
- Why didn’t Google Photos sync?
- Why do alerts not appear?
- Why is the slideshow empty?
- Why can’t backups/export run?

The page should prefer:
- concise summaries
- meaningful warnings
- actionable language

Avoid:
- walls of internal jargon
- developer-only stack trace dumps
- overly chatty “everything is fine” clutter

---

## 8. Remediation guidance

Where practical, each warning/error should include a short remediation hint.

Examples:
- “No active playable images found. Add or sync images to at least one active collection.”
- “Google Photos provider is configured but not connected. Reconnect the provider from Sources.”
- “Weather provider has not refreshed in 45 minutes. Check internet connectivity or provider credentials.”

This will make the page much more valuable.

---

## 9. Logging / diagnostics boundaries

The doctor page is not a full log viewer.

Do not turn it into:
- a stack trace console
- a general-purpose debug terminal
- a replacement for structured logs

It should summarize health state, not dump internals.

If useful, you may include:
- last error message snippet
- last sync status snippet

But keep it readable.

---

## 10. Optional nice-to-have features

These are encouraged but not required if they complicate delivery too much:

- copy diagnostics summary button
- export doctor report as JSON
- quick links to relevant admin pages (Sources, Weather, Collections, Backup)
- stale-data thresholds shown clearly
- Pi-specific runtime checks if easy and reliable:
  - disk usage
  - memory pressure
  - undervoltage/throttling hint
  - service status

Only include Pi runtime checks if they are straightforward and reliable in your existing architecture.

---

## 11. Testing

Add tests for:
- doctor aggregation logic
- severity rollup logic
- representative subsystem checks
- API response shape
- admin route protection

Use mocked/fake dependencies where appropriate.

The doctor service should be structured so it is easy to test healthy, degraded, and failing cases.

---

## 12. Documentation updates

Update:
- `README.md`
- `design/PRD.md`
- `design/SPEC.md`
- `design/ARD.md`

Also update or add user-facing docs under `docs/` if appropriate.

Add or update ADRs for:
1. doctor page as a first-class admin feature
2. normalized subsystem health reporting model
3. operator-friendly remediation guidance

Keep ADRs concise and decision-focused.

---

## 13. Constraints / Non-Goals

Do not:
- build a massive observability platform
- dump raw logs into the page
- expose the doctor page without admin auth
- tightly couple checks to one provider only
- make the page depend on internet reachability for basic rendering

Keep this feature:
- practical
- extensible
- readable
- admin-friendly
- useful for real troubleshooting

---

## 14. Acceptance Criteria

This work is complete when:

- a doctor page exists in the admin UI
- backend exposes aggregated doctor/health results
- major subsystems are checked and grouped
- warnings and errors are clearly surfaced
- remediation hints exist for common failure states
- provider/weather/display/collection health are represented where implemented
- admin auth protects the feature
- docs and ADR/SPEC updates are complete

---

## 15. Implementation Notes

Favor:
- normalized health result shapes
- modular subsystem checks
- actionable summaries
- conservative signal over noisy detail

Avoid:
- giant debug dumps
- brittle environment assumptions
- framework-heavy complexity
- checks that are expensive or unreliable on every refresh

Build the simplest good doctor page that a real admin would actually use.
