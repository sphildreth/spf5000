# ADR 0007: Use Browser Kiosk Runtime on the Pi

- Status: Accepted
- Date: 2026-03-15

## Context
SPF5000 needs to boot like an appliance on a Raspberry Pi, present a fullscreen slideshow, and support a small admin interface with minimal duplicated technology.

## Decision
Use a lightweight graphical session on the Pi, auto-launch Chromium in fullscreen kiosk mode, and render the display experience through the local web application at `/display`.

## Consequences
- Display and admin experiences can share a common frontend stack.
- Smooth transitions, overlays, and display tuning are easier than with a console or framebuffer-only renderer.
- Startup and watchdog behavior must account for browser and session management.
- The system remains more flexible than a custom native renderer while still feeling appliance-like.
