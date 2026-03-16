# ADR 0016: Use Cached Image-Derived Background Fill for Display Presentation

- Status: Proposed
- Date: 2026-03-16

## Context
SPF5000 already uses display-sized cached derivatives for slideshow playback (`0008`), keeps structured settings in DecentDB (`0003`), and stores image binaries plus generated variants on the filesystem (`0004`). The display experience now needs a configurable background treatment that helps portrait and mismatched-aspect images feel more intentional on `/display` without adding a visible black frame between slides or requiring expensive per-transition work from full originals.

The main implementation choices are to keep `/display` permanently black behind every image, derive background presentation from full originals at render time, or derive and cache background metadata from display-ready variants. The chosen approach must stay consistent with the existing offline-first cache strategy, keep runtime work predictable on Pi-class hardware, preserve ADR `0008`'s no-black-frame behavior, and degrade safely when metadata is missing or cannot be computed.

## Decision
SPF5000 should support image-derived background fill on `/display` with three modes: `black`, `dominant_color`, and `gradient`.

The selected background fill mode is stored as DecentDB-backed application state and managed like other display settings. Background metadata is derived from display-sized cached variants rather than full originals, then persisted with the asset metadata so the display runtime can reuse it without recomputing from source files. Older assets that predate this metadata may be backfilled lazily when they are next processed or displayed.

The renderer keeps background treatment separate from the two foreground slideshow layers established by ADR `0008`. Background fill therefore augments slide presentation without redefining the foreground transition model, and failures or unavailable metadata fall back to `black`.

## Consequences
- `/display` gains a configurable presentation improvement for portrait and aspect-mismatched images while keeping the existing cached-variant pipeline and Pi-friendly runtime behavior.
- DecentDB remains the source of truth for the selected mode, while asset metadata gains additional cached presentation data derived from filesystem-backed display variants.
- The system must generate, persist, and lazily backfill background metadata, which adds migration and cache-coherency work for older assets.
- The renderer becomes slightly more complex because background treatment and foreground slideshow layers must stay intentionally separate to preserve ADR `0008`'s no-black-frame transition rule.
