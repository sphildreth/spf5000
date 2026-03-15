# Product Requirements Document

## Product Name
Super Picture Frame 5000 (SPF5000)

## Summary
SPF5000 is a self-hosted, appliance-style digital picture frame platform intended to run on Raspberry Pi-class hardware. It is designed for users who want a simple, spouse-friendly digital frame experience without subscriptions, vendor lock-in, pairing friction, upload quotas, or mandatory cloud services.

## Problem Statement
Commercial digital picture frames often suffer from one or more of the following problems:

- recurring subscription requirements for basic functionality
- fragile or abandoned mobile applications
- dependence on third-party cloud services
- poor offline behavior
- complicated onboarding and image management flows
- low trust in long-term reliability

The target household wants a frame that behaves like an appliance, not a service relationship.

## Goals

1. Provide a simple, reliable digital frame experience on commodity hardware.
2. Support local administration from a web UI on the LAN.
3. Support multiple image sources over time through a provider model.
4. Prioritize offline-first behavior and cached playback.
5. Make the system resilient to power loss and temporary network failure.
6. Allow local image management directly on the device.
7. Allow future integration with user-selected Google Photos albums or ambient sources.
8. Present transitions that feel polished and continuous, without a visible black flash between images.

## Non-Goals for v1

- public multi-tenant SaaS hosting
- advanced user account management
- AI image tagging and semantic search on-device
- complex video-first playback
- a native non-browser renderer

## Target Users

### Primary User
Household member who wants a set-it-and-forget-it frame.

### Secondary User
Technical household member who installs, configures, and maintains the device.

## User Stories

### Display
- As a household member, I want the frame to boot directly into a slideshow.
- As a household member, I want the frame to keep showing photos even if the network is temporarily unavailable.
- As a household member, I want portrait and landscape images to display cleanly.
- As a household member, I want images to slide smoothly from left to right without a full black frame appearing between photos.

### Administration
- As an administrator, I want to configure slideshow timing and display behavior from a simple web page.
- As an administrator, I want to upload, remove, and organize pictures stored on the frame.
- As an administrator, I want to see sync and device health information.

### Sources
- As a household member, I want to select an album source and have pictures appear automatically on the frame.
- As an administrator, I want source integrations to sync into a local cache so playback is not dependent on live cloud responses.

## Functional Requirements

### Core Playback
- Display fullscreen slideshow on HDMI-connected monitor.
- Shuffle and sequential playback modes.
- Configurable dwell time per image.
- Configurable fit modes: contain, cover, smart center-fit.
- Automatic resume after reboot.
- Default transition mode should support horizontal slide animation with no visible full-black frame.
- Playback should use preloaded assets and never intentionally blank the screen during normal image-to-image transitions.

### Local Web UI
- Settings page
- Sources page
- Albums page
- Local media management page
- System status page

### Local Media Management
- Upload images from browser
- Delete images from device
- Organize images by albums or folders
- Maintain metadata and source origin in database

### Source Syncing
- Abstract provider model for source integrations
- Background sync job support
- Sync status persistence
- Cached local copies of remote images
- Graceful degradation when provider unavailable

### Persistence
- Store settings, metadata, sync state, and source mappings in DecentDB.
- Store image binaries and resized variants on local disk.

## Quality Attributes

### Reliability
- Device must recover from power interruption.
- Display page should remain functional even if admin UI unavailable.
- Cached playback should continue if remote providers or NAS shares are unavailable.

### Simplicity
- The admin UI should be understandable without technical training.
- The display experience should avoid intrusive overlays.
- Slideshow behavior should feel like a consumer appliance rather than a browser tab.

### Performance
- Pi 3 must be sufficient for v1 slideshow and admin flows.
- Remote images should be prefetched and cached.
- Display playback should avoid visible flicker during transitions.

### Maintainability
- Architectural decisions must be documented using ADRs.
- Data model and provider abstractions should support future expansion.
- Design artifacts should live under `design/` while future end-user documentation can live under `design/`.

## Risks
- Google Photos integration constraints may change or require specific APIs.
- Browser-based display rendering on low-power hardware may require tuning.
- Poorly bounded cache growth may consume disk unexpectedly.
- Some portable monitors may have undesirable wake, sleep, or power-loss behavior.

## Success Criteria
- Device boots to slideshow after power cycle.
- Admin can change settings and manage local images via browser on LAN.
- Cached playback continues if remote source is unavailable.
- Household member no longer depends on subscriptions or vendor mobile apps to display family photos.
- Transitions feel smooth and continuous, with no obvious black flash between images.
