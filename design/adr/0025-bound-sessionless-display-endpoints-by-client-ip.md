# ADR 0025: Bound sessionless display endpoints by client IP

- Status: Accepted
- Date: 2026-09-06

## Context

`/display` is public on purpose, so a growing set of JSON endpoints is reachable with no session at all: the playlist, the playback-progress companion added in ADR 0024, the weather and alert overlays, and the new-asset poll. Admin endpoints require a session, but nothing bounded the public ones. A misbehaving LAN client — or a compromised one — could hammer the device that is also the photo frame, and a playlist call is not free: it walks a collection, reconciles it against the database, and touches the playback-state row.

Sign-in and first-boot setup were the other unbounded pair, and those are precisely the endpoints worth brute-forcing.

Two facts constrain the fix:

- SPF5000 is a single-family appliance on a private network. Public requests carry no identity, so the only usable key is the source address.
- Playback must survive the limit. Progress reporting is deliberately fire-and-forget; the price of a rejected report is a lost resume position, never a visible failure.

## Decision

Rate limit every sessionless endpoint per client IP, using the in-process limiter that already guarded sign-in (`backend/app/api/rate_limit.py`), and declare the limit on the route that needs it through a `rate_limited("N/minute")` dependency so the budget is visible next to the endpoint.

| Endpoint | Limit |
| --- | --- |
| `POST /api/display/playlist/progress` | 240/minute |
| `GET /api/display/playlist` | 120/minute |
| `GET /api/display/new-assets/count` | 120/minute |
| `GET /api/display/weather` | 60/minute |
| `GET /api/display/alerts` | 60/minute |
| `POST /api/auth/login` | 10/minute |
| `POST /api/setup` | 5/minute |

Progress gets the largest budget because a frame reports on every transition on top of its playlist polling, and a lost resume position is the one regression this limit must never cause. The much tighter numbers below are for endpoints where volume has no legitimate explanation: a household signs itself in a handful of times a day, and first-boot setup happens once.

### Forwarded addresses are trusted only when declared

`client_ip()` keys on the peer address. `X-Forwarded-For` is consulted only when `SPF5000_TRUST_PROXY=true`. The app normally terminates HTTP itself on the Pi, so trusting a client-supplied header by default would let any LAN client choose the identity its own limit is applied against.

### One escape hatch, one process

`SPF5000_RATE_LIMIT=false` disables limiting entirely; the backend test suite relies on it. Counters are per process, which matches the deployment: the Pi runs a single uvicorn worker, so a shared store would add a dependency for no benefit. If the app is ever run with multiple workers, this decision has to be revisited.

### Playback treats rejection as expected

A 429 on the progress endpoint is neither retried nor surfaced in the UI, and the slideshow keeps advancing. This is asserted from the client side so the tolerance cannot be optimistically removed later.

## Consequences

### Positive

- Brute-forcing sign-in or first-boot setup is now throttled, and a runaway client cannot saturate the frame's own database work.
- Limits are declared where they apply, so a new public endpoint makes its budget an explicit choice during review.
- The proxy-trust decision is a single, auditable variable instead of implicit header sniffing.

### Negative

- Limits are advisory against a determined attacker with many source addresses; a shared NAT address also means shared budget.
- Per-process counters reset on restart, so a restart clears a throttle.
- A reverse-proxied deployment that forgets `SPF5000_TRUST_PROXY=true` limits every admin by the proxy's address instead of its own.

### Neutral

- `slowapi` remains the only runtime dependency providing this; the limiter itself stays small enough to replace without touching routes.
- The playlist's five-second cache still absorbs most read volume, so the limit is a runaway guard rather than a normal-path constraint.

## Related decisions

- ADR 0008 explains why `/display` is public in the first place, which is what makes these endpoints worth bounding.
- ADR 0024 defines the progress endpoint and its fire-and-forget semantics that make rejection tolerable.
