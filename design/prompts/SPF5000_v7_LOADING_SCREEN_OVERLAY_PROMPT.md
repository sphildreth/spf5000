# SPF5000 Boot Screen Implementation Prompt

You are implementing a retro 1980s-infomercial-inspired boot/loading screen for **SPF5000 (Super Picture Frame 5000)**.

## Goal

Use the provided finalized boot screen artwork as the static background, and render **dynamic loading/status text as a separate overlay layer** so the application can update messages in real time without regenerating or modifying the underlying image.

The final experience should feel polished, readable, and intentionally retro while remaining practical for real loading states.

---

## Background Asset Requirements

Use the finalized **black-background SPF5000 loading screen image** as the boot screen background.

Requirements:

* Keep the artwork intact.
* Treat the image as a static background layer.
* Do **not** bake loading text into the image.
* Dynamic text must be rendered by the app/UI as an overlay above the image.
* Preserve aspect ratio.
* Default to a black page/app background behind the image.

Recommended rendering behavior:

* `object-fit: contain` preferred for preserving the composition.
* `cover` is acceptable only if the composition remains visually safe on the target display.

---

## Layout and Safe Zones

The current artwork has strong visual elements in the center and lower-right areas, so place dynamic text only in designated safe zones.

### Primary safe zone

Use this as the default placement for the main dynamic status:

* Horizontal area: **22% to 78%**
* Vertical area: **74% to 88%**
* Alignment: **centered**

This area keeps text:

* below the main subtitle
* away from the monitor illustration
* away from the “As Seen on TV!” badge
* visually balanced on the screen

### Secondary safe zone

Optional placement for smaller secondary text:

* Horizontal area: **8% to 38%**
* Vertical area: **76% to 90%**

Use this only for small supporting text if needed.

### Avoid these areas

Do not place dynamic text in these locations:

* top-left (star flare)
* center (main SPF5000 logo and subtitle)
* right-middle (monitor graphic)
* bottom-right (“As Seen on TV!” burst)

---

## Functional Requirements

Implement a boot screen component/view that supports:

1. Static background image.
2. Main dynamic status text.
3. Optional sub-status text.
4. Optional animated ellipsis/dots.
5. Easy updates from real application boot state.
6. Clean fallback behavior when no detailed status is available.

### Main status text examples

* Preparing display
* Syncing content
* Checking schedule
* Loading media
* Rendering interface
* Almost ready
* Ready

### Optional sub-status examples

* Please wait…
* Contacting server
* Applying configuration
* Downloading latest assets
* Verifying local cache

---

## UX Requirements

The screen should feel:

* retro
* neon
* clean
* readable
* production-ready

### Visual styling for overlay text

Use a retro/digital style font if available, with sensible fallbacks.

Recommended font stack:

* Orbitron
* Rajdhani
* Arial
* sans-serif

### Main status style

* uppercase
* bold
* centered
* white or near-white text
* subtle glow/shadow for readability
* responsive font sizing
* high contrast against black background

### Sub-status style

* smaller than main status
* cyan/teal or soft neon accent color
* centered below main status
* subtle glow

### Readability rules

* Do not place text over busy parts of the image.
* Do not add a heavy opaque background box unless absolutely necessary.
* Prefer text-shadow/neon glow for readability first.
* Keep spacing generous.
* Handle long strings gracefully using wrapping, max width, and responsive scaling.

---

## Technical Requirements

Implement this as a reusable component appropriate for the project stack.

If this is a web frontend, create a component that:

* fills the viewport
* centers the background image
* overlays dynamic status text in the primary safe zone
* is responsive across common display sizes
* works well on a 1920x1080 display

### Behavior requirements

* Background is static.
* Overlay text is dynamic.
* Status should be updateable via props/state/store.
* Animated dots should be optional and easy to disable.
* The component should support either:

  * fake rotating demo messages for prototype mode, or
  * real app boot state messages for production mode

### Real-state preference

Prefer real status binding when available, such as:

* Initializing system
* Connecting to server
* Syncing frame settings
* Downloading playlist
* Rendering display
* Ready

---

## Implementation Guidance

Structure the boot screen with separate layers:

1. **Container layer**

   * full viewport
   * black background
   * relative positioning

2. **Background artwork layer**

   * absolute positioning
   * fills viewport
   * preserves aspect ratio
   * centered

3. **Overlay text layer**

   * absolute positioning
   * aligned to bottom-center safe zone
   * pointer-events disabled if appropriate

### Suggested positioning

Use the primary safe zone approximately like this:

* left: 50%
* top: 80%
* transform: translate(-50%, -50%)
* max width: constrained to avoid collisions
* centered text

---

## Example UI/CSS Direction

Use styling equivalent to the following ideas:

* full-screen black boot wrapper
* background image rendered with `object-fit: contain`
* centered overlay block near bottom
* main status with responsive font sizing using `clamp(...)`
* subtle white/cyan/magenta glow via text-shadow
* smaller cyan sub-status under main status

Do not treat this as a strict copy requirement, but the final implementation should achieve the same visual and layout goals.

---

## Optional Animated Dots

Support a lightweight animated ellipsis after the main status text.

Example behavior:

* Preparing display
* Preparing display.
* Preparing display..
* Preparing display...

Requirements:

* smooth
* low complexity
* easy to disable
* should not interfere with real status updates

---

## Edge Cases

Handle the following cleanly:

* very long status messages
* no sub-status provided
* no background image available
* slow initialization state
* finished/ready state
* different viewport sizes and aspect ratios

### Long text handling

* use max-width
* center align
* allow wrapping if needed
* avoid collision with artwork
* keep layout stable

---

## Deliverables

Produce the following:

1. Boot/loading screen component/view implementation.
2. Associated styles.
3. Example usage wired to mock status values.
4. Optional prototype/demo mode with rotating fake messages.
5. Production-ready hook/interface for real boot state updates.
6. Clear comments for integration points.

---

## Acceptance Criteria

The implementation is complete when:

* the SPF5000 black-background image is used as the static background
* the loading/status text is no longer baked into the image
* dynamic text is rendered in a safe overlay area
* text is readable and visually on-brand
* the component is responsive
* the monitor graphic and TV burst are not obstructed
* the solution works well on 1920x1080
* it can be wired to real loading states without redesign

---

## Nice-to-Have Enhancements

Consider these only if they do not overcomplicate the solution:

* gentle glow pulse on status text
* scanline or CRT shimmer overlay at very low intensity
* subtle fade transition between status messages
* accessibility improvements for reduced motion
* theme constants for easy tuning of text position and glow intensity

---

## Important Constraints

* Do not regenerate the artwork.
* Do not re-add a loading bar into the image.
* Do not place text in the bottom-right badge area.
* Do not put the text directly on top of the main SPF5000 logo.
* Keep the composition clean and production-appropriate.

---

## Final Instruction

Implement the boot screen in a way that is **easy to integrate, easy to maintain, and visually faithful to the retro SPF5000 branding**, with dynamic status text layered on top of the static artwork in a designated safe zone.
