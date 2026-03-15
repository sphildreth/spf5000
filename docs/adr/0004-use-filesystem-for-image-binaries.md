# ADR 0004: Use Filesystem for Image Binaries

- Status: Accepted
- Date: 2026-03-15

## Context
The system needs to store original and derived image files efficiently while keeping metadata queryable.

## Decision
Store image binaries on the filesystem and use DecentDB only for metadata.

## Consequences
- Simpler cache and storage management.
- Easier inspection and backup of images.
- Database remains small and focused on structured state.
