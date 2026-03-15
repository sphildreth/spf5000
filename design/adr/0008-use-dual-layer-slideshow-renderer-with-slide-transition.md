# ADR 0008: Use Dual-Layer Slideshow Renderer with Slide Transition

- Status: Accepted
- Date: 2026-03-15

## Context
The target household explicitly prefers a slideshow effect where the next image slides in from left to right without exposing a full black frame between images. Pi-class hardware also benefits from predictable rendering and preloading behavior.

## Decision
Implement the display renderer using two persistent image layers. The hidden layer preloads and decodes the next image, then transitions it into view with a horizontal slide effect while the current image exits. Playback uses display-sized cached derivatives rather than full originals.

## Consequences
- The slideshow can feel continuous and polished without visible blanking.
- The renderer remains simple enough for Pi 3-class hardware.
- Asset preparation and preload timing become first-class concerns in the display pipeline.
- Transition logic is more involved than naive single-image `src` swapping, but results should be materially better.
