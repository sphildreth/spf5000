# ADR 0009: Use Runtime Config and Single-Admin Bootstrap Auth

- Status: Accepted
- Date: 2026-03-15

## Context
The initial SPF5000 implementation assumed a trusted LAN with no authentication and relied on in-code runtime defaults. The follow-on implementation needs a simple first-run story, a durable way to supply runtime paths/bind settings, and a small authentication boundary that protects the admin UI without breaking the dedicated public `/display` route.

## Decision
Use a minimal external `spf5000.toml` file for startup/runtime concerns such as bind host/port, runtime paths, log level, and the optional session signing secret. Keep application settings, bootstrap state, and the single local admin record in DecentDB. Treat the system as bootstrapped when at least one enabled admin user exists, expose `/setup` only before that point, and protect `/admin` plus admin APIs with signed HTTP-only session cookies while keeping `/display`, the display playlist, and display asset fetches public.

## Consequences
- Runtime deployment concerns stay small and explicit while DecentDB remains the source of truth for app state.
- The appliance gains a clear first-run setup flow and a modest local-auth boundary without introducing PAM, OAuth, or multi-user RBAC.
- The backend and frontend must now coordinate setup/login/session state and route protection.
- Operators should provide a stable `security.session_secret` in production if they want sessions to survive backend restarts.
