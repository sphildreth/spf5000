# ADR 0021: Use Doctor Page as a First-Class Admin Health Feature

## Status

Accepted

## Context

SPF5000 is designed as an offline-first, self-hosted digital picture frame appliance. While the existing `/api/health` endpoint provides basic liveness information, operators need a single place to:

- Verify the frame is healthy after setup or configuration changes
- Troubleshoot problems without inspecting logs
- Confirm providers, weather, and alerts are working
- Identify degraded conditions before users notice them

The current system lacks a cohesive health-reporting surface that aggregates subsystem status into actionable operator guidance.

## Decision

We will implement a Doctor Page feature consisting of:

### Backend Components

1. **DoctorService** (`backend/app/services/doctor_service.py`)
   - Aggregates health checks from multiple subsystem checkers
   - Runs checks on demand via API
   - Returns normalized `DoctorResponse` with severity rollup

2. **Subsystem Checkers**
   - `ApplicationDoctorChecks`: App reachability, version, system time
   - `DatabaseDoctorChecks`: File existence, connection, schema validation
   - `StorageDoctorChecks`: Path existence, writability, disk space
   - `AuthDoctorChecks`: Authentication availability, admin user count
   - `MediaDoctorChecks`: Collections existence, playable assets, active collection
   - `ProviderDoctorChecks`: Source configuration and health per source
   - `WeatherDoctorChecks`: Weather enabled, location, provider status, data freshness
   - `DisplayDoctorChecks`: Display configuration, sleep schedule
   - `BackupDoctorChecks`: Export directory accessibility

3. **Health Check Schema** (`backend/app/schemas/doctor.py`)
   - `HealthCheck`: id, title, severity (ok/warning/error/info), summary, details, remediation
   - `HealthCheckGroup`: id, title, status, checks[]
   - `DoctorResponse`: overall_status, checked_at, groups[], summary

### API Endpoints

- `GET /api/admin/doctor` - Admin-protected health report
- `POST /api/admin/doctor/refresh` - Explicit refresh with logging
- `GET /api/admin/doctor/export` - JSON download for diagnostics

### Frontend Components

- `/admin/doctor` route in admin shell
- DoctorPage component with:
  - Overall status badge
  - Grouped health cards
  - Severity indicators (ok/warning/error/info)
  - Remediation hints where applicable
  - Refresh, copy summary, and export JSON actions

## Severity Model

Each check returns one of:

- `ok` - Subsystem is healthy
- `warning` - Subsystem is degraded but functional
- `error` - Subsystem is failing
- `info` - Informational status (e.g., feature disabled)

Group status is determined by the worst check severity (error > warning > info > ok).

Overall status is determined by the worst group status.

## Remediation Guidance

Each check may include a `remediation` hint that provides actionable guidance, such as:

- "No admin users configured. Complete initial setup."
- "Weather location not configured. Set a location in Weather settings."
- "No playable images found. Import images from Sources."

## Consequences

### Positive

- Single place for operators to verify system health
- Actionable guidance for common failure modes
- No log inspection required for basic troubleshooting
- Structured data enables future monitoring integrations

### Negative

- Additional API surface to maintain
- Health checks may need updates as features evolve
- Potential for check brittleness if dependencies change

### Neutral

- Doctor page is a new admin surface, not a breaking change
- Export functionality provides offline diagnostics capability

## Alternatives Considered

### Option 1: Extend existing /api/health endpoint

**Rejected** - The existing `/api/health` endpoint is intentionally minimal (ok + version + db_available). Expanding it would mix public health endpoints with admin-only diagnostics, confusing the API contract.

### Option 2: Dedicated observability platform

**Rejected** - A full observability stack (metrics, tracing, alerting) is overkill for a single-appliance deployment. The doctor page provides sufficient operator visibility without infrastructure complexity.

### Option 3: Interactive CLI tool

**Rejected** - While useful for SSH access, a CLI tool doesn't provide the visual, browser-based experience that matches the rest of the admin UI. Operators should be able to diagnose from the same interface they use for configuration.

## Implementation Notes

- Doctor endpoint requires admin authentication
- Checks are designed to be fast and non-destructive
- Each checker is isolated; one failing checker doesn't cascade
- Frontend uses existing admin layout and styling patterns
- Tests cover: severity rollup logic, API shape, auth protection
