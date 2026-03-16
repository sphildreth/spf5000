# ADR 0012: Use Google Photos Ambient API for Offline-First Local Asset Sync

- Status: Proposed
- Date: 2026-03-16

## Context
SPF5000 is intentionally offline-first at playback time. Accepted ADRs already establish that provider integrations sit behind a provider abstraction (`0005`), that metadata and sync state live in DecentDB (`0003`), that image binaries and generated variants live on the filesystem (`0004`), and that `/display` should render from locally prepared display assets without depending on remote fetches during slideshow playback (`0008`).

Google Photos support introduces a provider with stronger product and platform constraints than a generic cloud library integration. The supported Google model for ambient and device scenarios centers on the Google Photos Ambient API, device registration, a Google-managed settings UI for source selection, and OAuth 2.0 for TV and limited-input devices. That model is materially different from a legacy broad-library browsing integration where SPF5000 would enumerate and manage an entire remote photo library directly.

SPF5000 also needs to preserve its own provider-agnostic playback architecture. Once media is selected and synchronized, the slideshow pipeline should continue to operate on normalized local assets and local metadata rather than introducing provider-specific rendering behavior into `/display`.

## Decision
Implement Google Photos support as an ambient-style provider integration that uses the Google Photos Ambient API and the Google-supported device/ambient model rather than a broad-library browsing model.

The connection and source-selection flow will:

- use OAuth 2.0 for TV and limited-input devices (device-code flow)
- create and register the SPF5000 device with Google as required by the ambient integration model
- direct source selection to the Google Photos `settingsUri` rather than recreating Google media-selection UX inside SPF5000

The sync and playback model will:

- reflect Google-selected media sources into SPF5000 provider state as provider-managed source configuration and sync state
- keep provider-specific concerns at the integration and sync boundary rather than in the display runtime
- normalize synchronized Google Photos media into the existing local asset pipeline backed by DecentDB metadata and filesystem binaries
- keep `/display` strictly local-cache driven so slideshow playback continues even when the network or Google service is unavailable

## Consequences
- Google Photos support aligns with the supported Google ambient-device model instead of depending on legacy or over-broad library access patterns.
- `/display` remains provider-agnostic and offline-first because playback continues to use normalized local assets after sync.
- SPF5000 must implement device-code OAuth, device registration, provider state mapping, and sync orchestration specific to the Ambient API.
- Media choice UX is intentionally delegated to Google's `settingsUri`, which reduces custom UI scope but gives SPF5000 less direct control over remote source-browsing experience.
