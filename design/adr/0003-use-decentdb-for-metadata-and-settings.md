# ADR 0003: Use DecentDB for Metadata and Settings

- Status: Accepted
- Date: 2026-03-15

## Context
The project needs embedded persistence for settings, source metadata, sync state, and asset indexing. The author prefers DecentDB and wants the project to dogfood it directly.

## Decision
Use DecentDB as the embedded metadata database.

## Consequences
- Project aligns with author's preferred database model.
- Explicit SQL and repository abstractions are encouraged.
- Image binaries remain out of database storage.
