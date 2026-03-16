# SPF5000 Theme Definition Guide
## How to Create and Contribute Themes

This document explains how users, contributors, and coding agents should define themes for **SPF5000**.

The goal is to make theme creation:

- structured
- safe
- easy to review
- easy to contribute
- consistent across admin and display surfaces

---

# 1. What a Theme Is

A theme defines the visual style of SPF5000.

Themes influence things like:
- backgrounds
- cards
- text colors
- accent colors
- weather widget styling
- loading/empty-state styling
- home city visual treatment
- admin UI appearance
- display UI appearance

A theme does **not** change application logic.

Themes should never define:
- slideshow timing
- auth behavior
- alert escalation logic
- provider behavior

Themes are visual only.

---

# 2. Theme Philosophy

SPF5000 themes should use **semantic design tokens**.

That means theme values describe a visual role, not a specific feature.

Good examples:
- `color.surface`
- `color.textPrimary`
- `color.accentPrimary`

Bad examples:
- `weatherPurpleCard`
- `loginButtonBlue`
- `denverWidgetColor`

Themes should be reusable across the entire product.

---

# 3. Theme File Location

Recommended repository location:

```text
themes/
```

Examples:

```text
themes/default-dark.json
themes/retro-neon.json
themes/purple-dream.json
```

If the project later supports theme packs or alternate file formats, follow the same schema and conventions.

---

# 4. Recommended File Format

Recommended initial format:
- JSON

Why:
- easy to validate
- easy to load in backend/frontend tooling
- easy for coding agents to generate
- familiar to contributors

If the project later adopts TOML, the same conceptual structure should remain.

---

# 5. Required Theme Metadata

Each theme should include metadata.

Example:

```json
{
  "id": "purple-dream",
  "name": "Purple Dream",
  "description": "A rich purple-forward dark theme with neon-style accents.",
  "version": "1.0.0",
  "mode": "dark"
}
```

Required fields:
- `id`
- `name`
- `description`
- `version`
- `mode`

### Rules
- `id` should be lowercase kebab-case
- `name` should be user-friendly
- `description` should briefly explain the theme
- `version` should follow a simple version scheme such as `1.0.0`
- `mode` should currently be `dark` or `light`

---

# 6. Required Token Categories

A theme should define tokens in these categories:

- `colors`
- `typography`
- `shape`
- `effects`

If the app later expands token groups, keep the same structure.

---

# 7. Core Color Tokens

Recommended minimum color tokens:

```json
{
  "colors": {
    "background": "#0b0613",
    "backgroundAlt": "#120b1f",
    "surface": "#1a1027",
    "surfaceAlt": "#231535",
    "surfaceOverlay": "rgba(20, 10, 32, 0.78)",
    "textPrimary": "#f7f1ff",
    "textSecondary": "#c8b7df",
    "textMuted": "#9f8fb5",
    "border": "#5f3d89",
    "accentPrimary": "#b14cff",
    "accentSecondary": "#44d1ff",
    "success": "#46d39a",
    "warning": "#ffd34d",
    "error": "#ff5a72",
    "shadow": "rgba(0, 0, 0, 0.45)",
    "glow": "rgba(177, 76, 255, 0.35)",
    "overlayBackdrop": "rgba(0, 0, 0, 0.40)"
  }
}
```

### Guidance
- prefer tasteful, readable palettes
- do not make every token saturated neon unless intentionally stylistic
- ensure good text contrast
- use darker backgrounds for display overlays unless you have a strong reason not to

---

# 8. Typography Tokens

Recommended typography structure:

```json
{
  "typography": {
    "fontFamilyBase": "Inter, ui-sans-serif, system-ui, sans-serif",
    "fontFamilyDisplay": "Orbitron, Inter, ui-sans-serif, system-ui, sans-serif",
    "fontWeightNormal": 400,
    "fontWeightMedium": 500,
    "fontWeightBold": 700,
    "fontSizeBody": "16px",
    "fontSizeSmall": "13px",
    "fontSizeWidgetLabel": "13px",
    "fontSizeWidgetTemp": "42px",
    "fontSizeHeading": "24px",
    "fontSizeAlertHeadline": "52px",
    "fontSizeAlertSubheading": "24px"
  }
}
```

### Guidance
- prioritize readability
- display fonts should still be legible from a distance
- avoid novelty fonts that hurt clarity

---

# 9. Shape Tokens

Recommended shape structure:

```json
{
  "shape": {
    "radiusCard": "16px",
    "radiusButton": "10px",
    "radiusBadge": "999px",
    "radiusOverlay": "18px",
    "borderWidthStandard": "1px",
    "borderWidthEmphasis": "2px"
  }
}
```

### Guidance
- choose a coherent shape language
- rounded glass-like themes should stay consistently rounded
- sharp retro themes can use lower radii if desired

---

# 10. Effect Tokens

Recommended effects structure:

```json
{
  "effects": {
    "shadowCard": "0 10px 30px rgba(0,0,0,0.35)",
    "shadowOverlay": "0 16px 40px rgba(0,0,0,0.45)",
    "glowAccent": "0 0 20px rgba(177,76,255,0.25)",
    "glowLogo": "0 0 28px rgba(68,209,255,0.30)",
    "blurOverlay": "12px",
    "opacityWidgetBackground": 0.78,
    "opacityOverlayBackground": 0.40
  }
}
```

### Guidance
- use glows sparingly
- do not make the interface visually noisy
- keep overlays readable

---

# 11. Contextual Accent Defaults

Themes may define defaults for contextual accent rendering.

This is where features like **home city highlight style** can be influenced.

Example:

```json
{
  "contexts": {
    "weather": {
      "homeAccentDefault": "gradient_border"
    }
  }
}
```

Allowed values might include:
- `default`
- `subtle_border`
- `solid_border`
- `house_icon`
- `accent_glow`
- `gradient_border`
- `rainbow_gradient_border`

### Important
This does **not** force the app to use that style.
It defines the theme’s default preference.

---

# 12. Alert Safety Rules

Themes must not make critical alerts hard to read.

Do not redefine severe alert palettes in a way that breaks:
- red
- yellow
- black
- white

Critical fullscreen weather alerts must remain readable from across the room.

A theme may influence:
- spacing
- typography
- frame styling
- border radius

But not the core emergency readability model.

---

# 13. Recommended Theme File Example

```json
{
  "id": "purple-dream",
  "name": "Purple Dream",
  "description": "A rich purple-forward dark theme with layered gradients and soft neon accents.",
  "version": "1.0.0",
  "mode": "dark",
  "colors": {
    "background": "#0b0613",
    "backgroundAlt": "#120b1f",
    "surface": "#1a1027",
    "surfaceAlt": "#231535",
    "surfaceOverlay": "rgba(20, 10, 32, 0.78)",
    "textPrimary": "#f7f1ff",
    "textSecondary": "#c8b7df",
    "textMuted": "#9f8fb5",
    "border": "#5f3d89",
    "accentPrimary": "#b14cff",
    "accentSecondary": "#44d1ff",
    "success": "#46d39a",
    "warning": "#ffd34d",
    "error": "#ff5a72",
    "shadow": "rgba(0, 0, 0, 0.45)",
    "glow": "rgba(177, 76, 255, 0.35)",
    "overlayBackdrop": "rgba(0, 0, 0, 0.40)"
  },
  "typography": {
    "fontFamilyBase": "Inter, ui-sans-serif, system-ui, sans-serif",
    "fontFamilyDisplay": "Orbitron, Inter, ui-sans-serif, system-ui, sans-serif",
    "fontWeightNormal": 400,
    "fontWeightMedium": 500,
    "fontWeightBold": 700,
    "fontSizeBody": "16px",
    "fontSizeSmall": "13px",
    "fontSizeWidgetLabel": "13px",
    "fontSizeWidgetTemp": "42px",
    "fontSizeHeading": "24px",
    "fontSizeAlertHeadline": "52px",
    "fontSizeAlertSubheading": "24px"
  },
  "shape": {
    "radiusCard": "16px",
    "radiusButton": "10px",
    "radiusBadge": "999px",
    "radiusOverlay": "18px",
    "borderWidthStandard": "1px",
    "borderWidthEmphasis": "2px"
  },
  "effects": {
    "shadowCard": "0 10px 30px rgba(0,0,0,0.35)",
    "shadowOverlay": "0 16px 40px rgba(0,0,0,0.45)",
    "glowAccent": "0 0 20px rgba(177,76,255,0.25)",
    "glowLogo": "0 0 28px rgba(68,209,255,0.30)",
    "blurOverlay": "12px",
    "opacityWidgetBackground": 0.78,
    "opacityOverlayBackground": 0.40
  },
  "contexts": {
    "weather": {
      "homeAccentDefault": "rainbow_gradient_border"
    }
  }
}
```

---

# 14. Theme Creation Guidelines

When creating a theme:

1. Start with a clear visual idea
2. Choose readable background/text contrast first
3. Define accent colors second
4. Keep overlay readability in mind
5. Consider weather cards, loading screens, and admin UI all together
6. Be careful with glow and saturation
7. Test the theme on both:
   - admin UI
   - display UI

Good themes are coherent, not just colorful.

---

# 15. Contribution Guidelines

A contributed theme should include:
- the theme file
- a short description
- a preview screenshot if possible
- a note if it is intended for a specific aesthetic such as:
  - retro
  - modern
  - family-friendly
  - holiday
  - weather-centric

Contributors should avoid:
- missing required tokens
- unreadable text contrast
- hardcoded feature-specific values disguised as generic tokens
- novelty fonts that reduce usability

---

# 16. Coding Agent Guidance

When a coding agent creates a theme, it should:

- follow the documented theme schema
- use semantic tokens only
- include all required token categories
- produce valid JSON
- avoid inventing unsupported keys unless explicitly extending the schema
- prioritize readability and coherence
- avoid breaking severe alert readability rules

Coding agents should not:
- hardcode CSS in feature components instead of using tokens
- create feature-specific token names unless explicitly part of the schema
- bypass the theme file format

---

# 17. Recommended Built-In Starter Themes

Suggested built-in themes:
- `default-dark`
- `retro-neon`
- `purple-dream`

Optional later:
- `warm-family`
- `minimal-glass`
- `weather-channel-retro`

These give SPF5000 a strong starting set without overwhelming users.

---

# 18. Validation Expectations

All themes should be validated before use.

Validation should confirm:
- metadata exists
- required token groups exist
- required keys exist
- values are structurally valid
- missing optional sections are safely defaulted

Invalid themes should fail gracefully and not break the application.

---

# 19. Where This Fits in the Repo

Recommended placement:

```text
design/SPF5000_THEME_SYSTEM_DESIGN.md
docs/THEME_DEFINITION_GUIDE.md
themes/
```

This keeps:
- architecture/design docs under `design/`
- user/contributor docs under `docs/`
- actual themes under `themes/`

---

# 20. Summary

SPF5000 themes should be:
- structured
- validated
- semantic
- reusable
- contributor-friendly

Use:
- metadata
- semantic tokens
- contextual accent defaults

Do not use:
- hardcoded feature-specific theme values
- logic-changing theme definitions
- unreadable visual choices

A strong theme system will make SPF5000 feel more like a real product and will support personalization such as:
- purple-forward themes
- retro neon themes
- home-city rainbow gradient accents
- future seasonal and custom community themes
