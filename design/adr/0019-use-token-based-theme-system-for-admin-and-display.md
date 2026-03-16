# ADR 0019: Use Token-Based Theme System for Admin and Display

- Status: Proposed
- Date: 2026-03-16

## Context
SPF5000 styling now spans multiple surfaces and states instead of a small set of isolated admin pages. The product already includes or plans for fullscreen slideshow playback, weather widgets, alert overlays, boot and loading screens, empty states, and dynamic display backgrounds. A growing set of UI surfaces increases the risk of duplicated CSS, inconsistent styling, and feature-specific visual hacks.

The current frontend already relies on a small set of shared CSS variables in `frontend/src/styles/global.css`, but that is not yet a formal theme model. SPF5000 needs a stable visual contract that can support built-in themes, future contributed themes, and contextual treatments such as home-city highlighting without coupling styling decisions to application logic.

This decision also needs to stay consistent with existing architecture constraints:

- ADR `0002` keeps the frontend on React + TypeScript + Vite.
- ADR `0003` keeps settings and metadata in DecentDB while repository files remain appropriate for versioned assets and definitions.
- ADR `0008` keeps `/display` as a dedicated renderer whose styling must not interfere with the dual-layer slideshow behavior.
- ADR `0015` requires critical weather alerts to remain readable and deterministic on the display even when other overlay styling evolves.

## Decision
Adopt a token-based theme system that applies across both the admin UI and the `/display` experience.

The theme system will use these rules:

- Themes are structured data, not scattered feature-specific CSS fragments.
- Themes define semantic tokens first, then optional component-level overrides and contextual accent defaults.
- The theme model is split into a global theme layer and a contextual accent layer so special treatments such as home-city highlighting do not become hardcoded global defaults.
- Theme selection and theme-related user preferences such as `theme_id` and `home_city_accent_style` are stored in DecentDB application settings.
- Theme definitions themselves live as versioned files in the repository so they can be validated, reviewed, and shipped with the product.
- JSON is the initial file format because it is straightforward for backend validation and frontend consumption.
- The backend is responsible for loading and validating theme definition files and exposing available themes to the admin UI.
- The frontend consumes a shared semantic token model so admin and display surfaces stay visually coherent while still allowing display-specific readability overrides where needed.
- Critical fullscreen alert states keep a protected emergency palette and may only inherit safe framing details such as spacing, shape language, and restrained typography choices.
- Themes may influence presentation and motion styling, but they must not change slideshow timing, provider behavior, alert logic, authentication behavior, or other application rules.

## Consequences
- SPF5000 gains an explicit visual-system contract that can support built-in themes, contextual accents, and future theme contributions without scattering styling logic across features.
- Admin and display surfaces can share the same semantic token vocabulary while preserving existing `/display` and alert-safety constraints.
- Theme settings become part of the DecentDB-backed application configuration model, while theme definitions become a versioned repository asset that must be loaded and validated at runtime.
- Backend and frontend work both increase: schema validation, API exposure, safe fallbacks, and token-consumption patterns all need implementation before the system is fully usable.
- Critical alert presentation remains intentionally constrained, which limits theme freedom in emergency states but preserves appliance-grade readability and consistency.
