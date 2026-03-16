# SPF5000 Follow-On Implementation Prompt
## Dynamic Background Coloring / Image-Derived Screen Fill

You are working in the existing `spf5000` repository after the current in-flight work completes.

Your task is to implement **dynamic background coloring** for the fullscreen slideshow display.

The purpose of this feature is to improve presentation when an image does **not** fully fill the screen because of aspect-ratio differences.

Instead of always showing plain black around the image, SPF5000 should be able to derive a tasteful background treatment from the current image.

This is a display enhancement feature and must integrate cleanly with the existing slideshow architecture.

---

## Product Goal

When a photo does not fill the screen completely, SPF5000 should support background fill modes such as:

- solid black
- dominant color
- image-derived gradient
- blurred backdrop (optional/advanced mode)

This should make portrait photos and mixed-aspect-ratio albums look more polished and premium.

The feature must preserve:
- slideshow smoothness
- no-flicker transitions
- clear focus on the main image
- predictable behavior on Raspberry Pi hardware

---

## High-Level Requirements

Implement:

1. a configurable **background fill mode**
2. backend/storage support for the setting
3. admin UI controls for choosing the mode
4. display runtime behavior to render the chosen background treatment
5. documentation and ADR/SPEC updates

The implementation must be careful not to introduce slideshow jank.

---

## 1. Supported Modes

Implement the following background fill modes:

- `black`
- `dominant_color`
- `gradient`

### Optional / stretch goal
- `blurred_backdrop`

If time or complexity becomes an issue, complete the first three modes well before attempting `blurred_backdrop`.

### Mode meanings

#### black
Current/default behavior.
Unused screen space is filled with black.

#### dominant_color
Extract a representative dominant color from the current image and use it as the background.

#### gradient
Extract multiple representative colors from the current image and use them to render a tasteful background gradient.

#### blurred_backdrop
Use an enlarged blurred version of the same image behind the foreground image.
This mode is optional in this slice unless implementation proves straightforward and performant.

---

## 2. Behavioral Rules

This feature is only relevant when the foreground image does not fill the full display area.

Requirements:
- preserve the main image aspect ratio
- do not distort the foreground image
- background treatment must remain visually behind the main image
- background must not overpower the image
- slideshow transitions must remain smooth
- no black flash should appear between normal image-to-image transitions unless black mode is selected and is the intended persistent background

The foreground image must remain the primary visual focus.

---

## 3. Recommended Visual Treatment

### dominant_color
Use a muted, slightly darkened version of the extracted color rather than a fully saturated raw value.

### gradient
Use a tasteful 2-color or 3-color gradient derived from the image palette.
The gradient should feel calm and supportive, not loud.

Recommended guidance:
- prefer darker / softened tones
- avoid extremely high saturation where possible
- maintain good contrast with the foreground image edges

### blurred_backdrop
If implemented:
- heavily blur the background image
- dim it somewhat
- optionally reduce saturation slightly
- ensure the foreground image remains clearly readable/focused

---

## 4. Performance Requirements

This feature must be designed for appliance-style slideshow playback on Raspberry Pi hardware.

Requirements:
- do not perform expensive palette extraction in a way that blocks transitions
- do not repeatedly analyze giant original images at display time
- prefer deriving the background treatment from already-cached display-sized images or precomputed metadata
- keep rendering predictable and lightweight

### Strong recommendation
Compute background color/palette information from display-sized cached images rather than full originals whenever practical.

If palette extraction is expensive, compute it once during asset preparation or first-use caching and persist the result.

---

## 5. Persistence / Settings

Store the chosen background fill mode in DecentDB as an application setting.

Suggested setting:

- `background_fill_mode`

Allowed values:
- `black`
- `dominant_color`
- `gradient`
- `blurred_backdrop` (only if implemented)

If needed, optionally add future-facing settings, but keep v1 modest.

Potential future settings:
- `background_dim_percent`
- `background_blur_strength`
- `background_saturation_percent`

These are not required unless implementation naturally supports them.

---

## 6. Admin UI

Add admin UI controls for the background fill mode.

Requirements:
- setting is editable in the admin UI
- current value loads correctly
- user can save changes
- change affects future display behavior
- UI labels are understandable

Suggested label:
- **Image background fill**

Suggested options:
- Black
- Dominant Color
- Gradient
- Blurred Backdrop (if implemented)

If the project already has a Display Settings page, integrate there.

---

## 7. Display Implementation

Update the display route logic/components to support dynamic background rendering.

Requirements:
- background treatment updates per-image as needed
- transitions remain smooth
- background and foreground transitions should feel intentional
- avoid visible reflow or flashing when changing from one image to another

A practical implementation may include:
- background layer
- foreground image layer
- preloaded next image/background metadata
- synchronized transition timing

The existing no-flicker slideshow architecture should be respected.

---

## 8. Precomputation / Metadata Strategy

A strong implementation approach is to associate each displayable asset with derived visual metadata, for example:

```json
{
  "dominant_color": "#2f4a63",
  "gradient_colors": ["#2f4a63", "#8a6c52"],
  "background_ready": true
}
```

This metadata may be:
- computed during asset ingestion
- computed on first playback and cached
- stored in DecentDB or asset metadata storage

Choose a clean approach consistent with the current architecture.

The important goal is to avoid unnecessary repeated expensive analysis during playback.

---

## 9. Mode Fallbacks

If dynamic background generation fails for an image:
- fall back gracefully to `black`
- do not break slideshow rendering
- do not surface ugly errors on the display route

If a mode is selected but data is not yet ready:
- use a safe fallback until metadata is available
- avoid blocking playback

---

## 10. Testing

Add tests for:
- allowed setting values
- persistence of background fill mode
- fallback behavior
- image metadata/palette extraction logic where practical
- display rendering/state behavior if the frontend test setup supports it

The code should be structured to make palette/background derivation testable.

---

## 11. Documentation Updates

Update the relevant documentation.

At minimum update:
- `README.md`
- `design/PRD.md`
- `design/SPEC.md`
- `design/ARD.md`

Add or update ADRs as appropriate to reflect:
- image-derived background fill as a slideshow presentation decision
- preference for precomputed/cached metadata over expensive live analysis during display rendering

Keep ADRs concise and focused on architecture/decision reasoning.

---

## 12. Constraints / Non-Goals

Do not:
- distort foreground images
- let dynamic backgrounds overwhelm the photo
- introduce frame drops or obvious transition stutter
- tightly couple this feature to one specific provider or asset source
- assume all images are landscape

This feature should work cleanly with:
- local files
- Google Photos synced assets
- future providers

---

## 13. Acceptance Criteria

This work is complete when:

- admin can choose a background fill mode
- setting is stored in DecentDB
- display route supports at least:
  - black
  - dominant_color
  - gradient
- portrait and mixed-aspect-ratio images render with the selected background treatment
- slideshow remains smooth and no-flicker
- failures fall back safely
- docs and ADR/SPEC updates are complete

If `blurred_backdrop` is also implemented well and performantly, that is a bonus.

---

## 14. Implementation Notes

Favor:
- tasteful visuals
- performance-aware implementation
- precomputed metadata where possible
- simple admin UX
- safe fallback behavior

Avoid:
- overly clever live image analysis during every transition
- loud/saturated backgrounds
- performance regressions
- introducing complexity before the first three modes are done well

Build the simplest good first version.
