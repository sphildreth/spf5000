# SPF5000 Configuration Reference

This document describes the schema for `spf5000.toml`, the runtime configuration file for SPF5000.

## Location

By default, `spf5000.toml` is expected in the repository root (the same directory as `backend/` and `frontend/`). To use a different path, set the `SPF5000_CONFIG` environment variable:

```bash
SPF5000_CONFIG=/etc/spf5000/spf5000.toml
```

## Minimal Example

```toml
[server]
host = "0.0.0.0"
port = 8000
debug = false

[security]
session_secret = "replace-with-a-64-char-random-hex-string"

[providers.google_photos]
client_id = "your-client-id.apps.googleusercontent.com"
client_secret = "your-client-secret"
sync_cadence_seconds = 3600
```

---

## Section: `[server]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `host` | string | `"0.0.0.0"` | Host address to bind the FastAPI server to. Use `127.0.0.1` for localhost-only. |
| `port` | integer | `8000` | TCP port to listen on. |
| `debug` | boolean | `false` | Enable FastAPI debug mode (reload, verbose errors). **Never enable in production.** |

---

## Section: `[paths]`

All paths support both absolute paths and relative paths (relative to the `spf5000.toml` directory).

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `data_dir` | string | `"./data"` | Root directory for DecentDB, originals, variants, and staging. |
| `cache_dir` | string | `"./cache"` | Directory for temporary/transient files (downloads, sync staging). |
| `log_dir` | string | `"./logs"` | Directory for rotated log files. |
| `database_path` | string | `"{data_dir}/spf5000.ddb"` | Path to the DecentDB database file. |

---

## Section: `[logging]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `level` | string | `"INFO"` | Python logging level. Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |

---

## Section: `[security]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `session_secret` | string | *(none)* | 64-character hex string used to sign session cookies. **Required for production.** Generate with: `python -c "import secrets; print(secrets.token_hex(32))"`. Without this, an ephemeral secret is used and sessions are invalidated on every server restart. |
| `session_https_only` | boolean | `false` | When `true`, session cookies are marked `Secure` and `HttpOnly` and only sent over HTTPS. Enable this when the app runs behind a TLS-terminating reverse proxy (e.g., nginx + Let's Encrypt). **Do not enable on plain HTTP.** |
| `rate_limit_enabled` | boolean | `true` | Enable per-endpoint rate limiting on auth endpoints. Disable for development or environments without the `slowapi` package. |

---

## Section: `[providers.google_photos]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `client_id` | string | *(none)* | OAuth 2.0 client ID from Google Cloud Console. Required for Google Photos sync. |
| `client_secret` | string | *(none)* | OAuth 2.0 client secret from Google Cloud Console. |
| `provider_display_name` | string | `"Google Photos"` | Human-readable name shown in the admin UI for this provider. |
| `sync_cadence_seconds` | integer | `3600` | Minimum interval between automatic Google Photos sync runs (in seconds). Actual runs may be less frequent if sync completes quickly. |

---

## Environment Variables

Environment variables take precedence over `spf5000.toml` settings for most values.

| Variable | Description |
|----------|-------------|
| `SPF5000_CONFIG` | Path to `spf5000.toml` |
| `DECENTDB_NATIVE_LIB` | Path to `libdecentdb.so` / `decentdb.dll` (if not in system library path) |
| `SPF5000_DATA_DIR` | Override `[paths].data_dir` |
| `SPF5000_CACHE_DIR` | Override `[paths].cache_dir` |
| `SPF5000_LOG_DIR` | Override `[paths].log_dir` |
| `SPF5000_LOG_LEVEL` | Override `[logging].level` |
| `SPF5000_RATE_LIMIT` | Override `[security].rate_limit_enabled` (`true` / `false`) |
| `GOOGLE_OAUTH_CLIENT_ID` | Override `[providers.google_photos].client_id` |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Override `[providers.google_photos].client_secret` |
| `NWS_API_KEY` | API key for the National Weather Service API (improves rate limits) |
| `SESSION_SECRET` | Override `[security].session_secret` |
