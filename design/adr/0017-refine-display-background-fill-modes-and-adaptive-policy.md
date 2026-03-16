# ADR 0017: Refine Display Background Fill Modes and Adaptive Policy

- Status: Proposed
- Date: 2026-03-16

## Context
ADR `0016` established cached image-derived background fill for `/display` using display-sized variants instead of full originals. That remains the right foundation for color-based presentation, but expanded background treatments do not all need the same data path.

Color-driven modes such as `dominant_color`, `gradient`, `soft_vignette`, and `palette_wash` benefit from cached metadata derived from the display variant and persisted with the asset record. Image-based treatments such as `blurred_backdrop` and `mirrored_edges` can instead reuse the already generated display variant at render time. The display also needs an automatic policy that chooses a suitable treatment when aspect mismatch is significant without forcing administrators to pick one fixed effect for every image.

## Decision
This ADR refines ADR `0016` rather than replacing it. SPF5000 should support the display background modes `black`, `dominant_color`, `gradient`, `soft_vignette`, `palette_wash`, `blurred_backdrop`, `mirrored_edges`, and `adaptive_auto`.

Cached display-variant metadata remains the source of truth for color-based modes. `dominant_color`, `gradient`, `soft_vignette`, and `palette_wash` continue to use metadata derived from display-sized cached variants and persisted with asset metadata so `/display` can render them without recomputing from full originals. `black` requires no derived metadata.

`blurred_backdrop` and `mirrored_edges` are image-based presentation modes. They may reuse the display-sized variant directly at render time instead of requiring a separate cached color-metadata format beyond what ADR `0016` already introduced.

`adaptive_auto` is a display-behavior policy, not a separate derived-asset format. At render time it chooses among supported treatments based on aspect mismatch and the cached metadata available for that asset, falling back to simpler supported treatments when richer presentation data is unavailable.

Background treatment remains separate from the two foreground slideshow layers established by ADR `0008`, and it must preserve the no-black-frame transition rule during normal slide changes.

## Consequences
- SPF5000 can offer richer portrait and mixed-aspect presentation without discarding ADR `0016`'s cached-metadata approach for color-based modes.
- The renderer can use the existing display variant for image-based treatments, which avoids pushing full-original analysis into slideshow playback.
- Additional color-based treatments can be added without redefining the storage split as long as they continue to rely on cached display-variant metadata.
- The display runtime becomes more policy-driven because `adaptive_auto` must make deterministic choices from aspect mismatch and available cached metadata.
- Documentation and implementation must distinguish cached color metadata from render-time image-based treatments so storage and playback responsibilities stay clear.
