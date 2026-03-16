# SPF5000 Follow-On Implementation Prompt
## Bootstrap Auth + Runtime Config

You are working in the existing `spf5000` repository after the initial scaffold and v1 implementation work has completed.

Your task is to implement **runtime configuration**, **first-run bootstrap**, and **single-admin authentication** for SPF5000.

Follow the project architecture and existing docs/ADRs. Update documentation where needed.

---

## Goals

Implement the following:

1. A minimal external runtime config file named **`spf5000.toml`**
2. Keep **DecentDB** as the source of truth for application settings and bootstrap state
3. Add **first-run setup flow** at `/setup` when no admin user exists
4. Add **single-admin local authentication**
5. Add **session-cookie based auth** for the admin UI and admin API
6. Prevent access to `/setup` once bootstrap is complete
7. Update design docs and ADRs to reflect the final implementation

---

## Architectural Rules

### Runtime config vs app config

Use this split:

#### `spf5000.toml`
This file is only for startup/runtime concerns, such as:
- database file path
- cache root path
- bind host
- bind port
- log level
- dev mode flag if needed

#### DecentDB
DecentDB remains the source of truth for:
- app settings
- slideshow settings
- transition settings
- selected sources/albums
- bootstrap state
- admin user records
- session/auth-related app data if needed
- system/device preferences

Do **not** put slideshow settings or admin password hashes in `spf5000.toml`.

---

## Required Features

## 1. Runtime config file

Add support for loading runtime config from a file named:

- `spf5000.toml`

Design a small config structure like:

```toml
[server]
host = "0.0.0.0"
port = 8000

[paths]
data_dir = "./data"
cache_dir = "./cache"
database_path = "./data/spf5000.ddb"

[logging]
level = "INFO"
```

Requirements:
- reasonable defaults if the file is missing
- support overriding path to config file if helpful
- keep parsing implementation simple and maintainable
- document the config file in the repo

---

## 2. DecentDB bootstrap state

Ensure schema/tables exist for:
- admin users
- system state
- app settings

Implement logic so startup checks whether any enabled admin user exists.

If no enabled admin user exists:
- system is considered **not bootstrapped**
- `/admin` should redirect to `/setup`
- `/setup` should be accessible

If an enabled admin user exists:
- system is considered **bootstrapped**
- `/setup` should be blocked or redirected away
- `/admin` requires login

---

## 3. First-run setup flow

Implement a setup page at:

- `GET /setup`
- `POST /api/setup`

Setup page requirements:
- only usable when no enabled admin user exists
- form fields:
  - admin username
  - password
  - confirm password
- validate:
  - username non-empty
  - password minimum reasonable length
  - confirm matches
- on success:
  - create admin user
  - store password hash
  - mark bootstrap complete in DB if you choose to track it explicitly
  - create authenticated session
  - redirect user into `/admin`

After setup succeeds:
- `/setup` should no longer be usable unless there are zero enabled admin users again

---

## 4. Authentication model

Implement **single-admin local auth** with app-managed credentials.

Requirements:
- local username/password auth
- password stored as a secure password hash
- no plain-text storage
- no PAM
- no external identity provider
- no OAuth
- no extra auth service

Use a well-established Python password hashing approach.

Suggested route shape:
- `GET /login`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/session`

Behavior:
- successful login creates authenticated session
- failed login returns clear validation error
- logout clears session
- session endpoint returns authenticated user info or unauthenticated state

Keep implementation small and understandable.

---

## 5. Session handling

Use secure cookie-backed sessions.

Requirements:
- signed session cookie
- HTTP-only cookie
- sensible expiration behavior
- same-site protection
- production-minded defaults where reasonable for LAN-only use

Protect:
- admin pages
- admin APIs
- setup completion logic after bootstrap

Public display routes should remain accessible without admin auth:
- `/display`
- display asset fetch routes if required for slideshow operation

---

## 6. Admin route protection

Implement route guards for:
- admin frontend routes
- admin API routes

Desired behavior:
- unauthenticated access to `/admin` redirects to `/login`
- unauthenticated access to protected admin APIs returns `401`
- bootstrapping state is respected before normal login flow

---

## 7. Frontend changes

Update the React frontend to include:
- setup page
- login page
- logout action
- basic session-aware admin shell behavior

Requirements:
- clean, minimal UI
- no large UI library unless already present
- keep styles simple
- show useful validation messages
- handle redirects cleanly

Suggested pages:
- `/setup`
- `/login`
- `/admin`

If your frontend router/layout already exists, integrate cleanly into it.

---

## 8. Repository/data layer changes

Add repository/service support for:
- create admin user
- get admin by username
- count enabled admins
- verify password
- read/write bootstrap/system state
- read runtime-aware settings as needed

Prefer explicit SQL and simple repository methods.
Stay aligned with the existing DecentDB direction of the repo.

---

## 9. Documentation updates

Update the repo documentation to reflect the implementation.

At minimum update:
- `README.md`
- `design/PRD.md`
- `design/SPEC.md`
- `design/ARD.md`
- relevant ADRs
- ADR index if present

Add or update ADRs to reflect:
1. minimal runtime config via `spf5000.toml`
2. app-managed single-admin authentication
3. first-run bootstrap via `/setup`
4. DecentDB as source of truth for application settings and bootstrap state

Keep ADRs concise and decision-oriented.

---

## 10. Constraints

- Keep it KISS
- No PAM
- No helper auth daemon/service
- No external auth provider
- No overengineered RBAC
- No multi-user system for v1
- Do not break the fullscreen slideshow/display flow
- Keep `/display` appliance-friendly and unauthenticated

---

## Acceptance Criteria

Implementation is complete when:

- app can start with or without `spf5000.toml`
- runtime config loads successfully
- DecentDB schema supports admin/bootstrap state
- fresh install with no admin redirects to `/setup`
- setup creates first admin successfully
- setup becomes unavailable after bootstrap
- login/logout work
- protected admin routes require auth
- display routes remain accessible
- docs and ADRs are updated
- code is clean and consistent with the repo structure

---

## Suggested Deliverables

- updated backend code
- updated frontend code
- updated repositories/services
- updated docs
- updated ADRs
- example `spf5000.toml`
- migration/schema updates if applicable

---

## Implementation Notes

Keep the implementation intentionally modest. This is a LAN-only appliance admin UI, not a SaaS product.

Favor:
- clarity
- maintainability
- explicitness
- good defaults

Avoid:
- unnecessary abstractions
- enterprise auth complexity
- speculative future-user systems

Build the simplest good version.
