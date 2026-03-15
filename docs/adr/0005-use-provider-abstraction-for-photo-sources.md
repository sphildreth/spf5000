# ADR 0005: Use Provider Abstraction for Photo Sources

- Status: Accepted
- Date: 2026-03-15

## Context
The project must support multiple image origins over time, including local files and remote services such as Google Photos.

## Decision
Introduce a provider abstraction layer for photo sources.

## Consequences
- Future source integrations can be added without reworking core slideshow logic.
- Sync orchestration and UI can remain provider-agnostic.
- Slightly more indirection in the codebase, but substantially better extensibility.
