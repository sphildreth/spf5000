# SPF5000 Theme System Design
## Theme Architecture, Scope, Tokens, and Runtime Behavior

This document defines the theme system for **SPF5000**.

The goal is to create a consistent, extensible visual system that can style both:

- the **admin UI**
- the **display UI**

without turning styling into a collection of one-off hardcoded CSS decisions.

This theme system must support:

- core product branding
- family-friendly customization
- strong default themes
- contextual accents such as **home city highlighting**
- future theme contributions by users and coding agents

This document is intended as an internal architecture/design reference.

---

# 1. Why SPF5000 Needs a Theme System

SPF5000 now includes or plans to include:

- fullscreen slideshow display
- boot/loading screens
- empty-state screens
- weather widget overlays
- multi-city weather card rotation
- home city highlighting
- severe weather alert screens
- admin UI
- dynamic background coloring

At this point, styling choices are no longer isolated UI details. They form a **visual system**.

Without a theme system, the project risks:
- inconsistent styling
- duplicated CSS
- one-off feature-specific hacks
- difficulty adding new look-and-feel presets
- difficulty for contributors to create polished themes

A formal theme system solves this.

---

# 2. Theme System Goals

The SPF5000 theme system should:

1. Provide a **shared visual language** across admin and display surfaces
2. Use **semantic design tokens**, not feature-specific hardcoded colors
3. Support multiple built-in themes
4. Support optional contextual accent styling
5. Keep critical alert readability safe even under heavy theming
6. Make it easy for users and contributors to create new themes
7. Allow future theme packs without refactoring the product

---

# 3. Theme Layers

SPF5000 themes should have **two layers**.

## 3.1 Global Theme Layer
This defines the overall visual language of the product.

It affects:
- backgrounds
- cards/panels
- text colors
- buttons
- form controls
- weather widgets
- boot/loading screens
- empty states
- slideshow overlays
- logo presentation
- border radii
- glows/shadows

## 3.2 Contextual Accent Layer
This defines styling applied to specific states or entities.

Examples:
- home city accent
- special album accent
- holiday mode accent
- selected/highlighted weather location
- low-priority alert badge accent

This allows SPF5000 to support special treatments like:

- `gradient_border`
- `rainbow_gradient_border`
- `house_icon`
- `subtle_glow`

without forcing those to become global theme defaults.

---

# 4. What Themes Affect

## 4.1 Admin UI
Themes affect:
- page background
- cards and panels
- buttons
- navigation
- forms
- section headers
- tables/lists
- badges
- charts/status cards
- logo/branding presentation

## 4.2 Display UI
Themes affect:
- weather widget
- weather card rotator styling
- home city accent treatment
- loading screen
- empty-state screen
- slideshow overlay chrome
- dynamic background coloring defaults
- card background opacity/tint
- text styles for overlays

## 4.3 Alert UI
Themes may affect:
- typeface choices
- spacing
- border radius
- frame style
- shadow/glow restraint

But themes must **not compromise alert readability**.

Critical alerts should reserve:
- red
- yellow
- black
- white

The theme system may decorate alert layout, but must not override the core emergency palette beyond safe bounds.

---

# 5. What Themes Should Not Control

Themes should not directly control:
- slideshow timing
- provider behavior
- auth flows
- alert logic
- state transitions
- business rules

Themes style the product. They do not change application logic.

---

# 6. Theme Model

Each theme should be represented as structured data rather than scattered CSS fragments.

Suggested shape:

```json
{
  "id": "retro-neon-purple",
  "name": "Retro Neon Purple",
  "description": "A dark neon theme with purple-forward accents.",
  "version": "1.0.0",
  "mode": "dark",
  "tokens": {},
  "components": {},
  "contexts": {}
}
```

A theme should contain:
- metadata
- design tokens
- optional component-level overrides
- optional contextual accent defaults

---

# 7. Design Token Philosophy

Use **semantic design tokens** rather than feature-specific literal values.

Good:
- `color.surface`
- `color.textPrimary`
- `color.accentPrimary`

Bad:
- `weatherCardPurple`
- `adminButtonBlue`
- `loadingScreenPink`

Semantic tokens make themes reusable across the entire product.

---

# 8. Token Categories

## 8.1 Color Tokens
Suggested core tokens:

- `color.background`
- `color.backgroundAlt`
- `color.surface`
- `color.surfaceAlt`
- `color.surfaceOverlay`
- `color.textPrimary`
- `color.textSecondary`
- `color.textMuted`
- `color.border`
- `color.accentPrimary`
- `color.accentSecondary`
- `color.success`
- `color.warning`
- `color.error`
- `color.shadow`
- `color.glow`
- `color.overlayBackdrop`

## 8.2 Typography Tokens
Suggested typography tokens:

- `font.family.base`
- `font.family.display`
- `font.weight.normal`
- `font.weight.medium`
- `font.weight.bold`
- `font.size.body`
- `font.size.small`
- `font.size.widgetLabel`
- `font.size.widgetTemp`
- `font.size.heading`
- `font.size.alertHeadline`
- `font.size.alertSubheading`

## 8.3 Shape Tokens
Suggested shape tokens:

- `radius.card`
- `radius.button`
- `radius.badge`
- `radius.overlay`
- `border.width.standard`
- `border.width.emphasis`

## 8.4 Effect Tokens
Suggested effect tokens:

- `shadow.card`
- `shadow.overlay`
- `glow.accent`
- `glow.logo`
- `blur.overlay`
- `opacity.widgetBackground`
- `opacity.overlayBackground`

## 8.5 Motion Tokens
Suggested motion tokens:

- `motion.fast`
- `motion.normal`
- `motion.slow`
- `easing.standard`
- `easing.emphasized`

These should influence how themed UI elements animate, while slideshow logic remains separate.

---

# 9. Component-Level Theming

After core tokens, SPF5000 can define component-level theme application.

Suggested themed components:

- admin shell
- cards
- buttons
- weather widget
- multi-city weather rotator card
- loading screen
- empty-state screen
- info overlays
- badges
- home city treatment

Component styles should consume semantic tokens first, not bypass them.

---

# 10. Contextual Accent System

A contextual accent system allows special treatments without polluting global theme defaults.

## 10.1 Home City Accent
Home city should be configurable independently from the global theme.

Suggested allowed values:
- `default`
- `subtle_border`
- `solid_border`
- `house_icon`
- `accent_glow`
- `gradient_border`
- `rainbow_gradient_border`

The current theme defines how these render visually.

## 10.2 Alert Accent
Lower-severity badges/banners may use themed framing, but fullscreen critical alerts should retain protected emergency styling.

## 10.3 Event Accent
Future use:
- holiday modes
- anniversary modes
- special family event themes

---

# 11. Theme Presets to Ship First

Recommended initial built-in themes:

## 11.1 Default Dark
Neutral, modern, safe.

## 11.2 Retro Neon
Fits SPF5000 branding.
Dark base, neon cyan/magenta accents, subtle glow.

## 11.3 Purple Dream
Wife-approved.
Purple-forward hues, layered gradients, rich accent palette.

## 11.4 Warm Family
Softer gold/rose/cream tones for a cozy household look.

Optional later:
- Minimal Glass
- Weather Channel Retro
- Holiday Themes

---

# 12. Theme and Alert Safety

Critical alerts must not become unreadable because of theming.

Rules:
- fullscreen emergency states always use protected emergency palette
- theme can influence layout framing, shape language, and typography
- theme cannot override the core red/yellow/black/white readability model for critical alerts

This should be documented as a hard product rule.

---

# 13. Theme Application Scope

Themes should apply to both:
- admin UI
- display UI

This ensures the product feels coherent.

However, display-specific contexts may override some tokens for readability or atmosphere, such as:
- display overlay opacity
- loading screen glow intensity
- weather card translucency

---

# 14. Storage and Runtime Model

Theme selection should be stored in **DecentDB** as application settings.

Suggested settings:
- `theme_id`
- `home_city_accent_style`
- optional future display overrides

Theme definitions themselves should live as files in the repository, not in the database.

Suggested directory:

```text
themes/
  default-dark.json
  retro-neon.json
  purple-dream.json
```

Or equivalent TOML if preferred.

The runtime loads available themes from disk, validates them, and exposes them to admin UI.

---

# 15. Validation Model

Theme files should be validated before use.

Validation should ensure:
- required metadata exists
- required tokens exist
- values are structurally valid
- unsupported token keys are either rejected or warned on
- missing optional sections are safely defaulted

This allows user-contributed themes without destabilizing the app.

---

# 16. Theme Inheritance (Optional Future)

A future enhancement could allow themes to extend other themes.

Example:
- `purple-dream` extends `default-dark`
- overrides only accent colors and widget styling

Not required for first implementation, but worth keeping in mind.

---

# 17. Admin UI Requirements

The admin UI should allow:
- choosing active theme
- previewing available built-in themes
- choosing home city accent style
- optionally later importing custom themes

Initial UI can be modest:
- theme select dropdown
- home city accent style dropdown
- small preview swatches/cards

---

# 18. Multi-City Weather and Themes

The theme system should be defined **before** implementing the multi-city weather rotator.

Reason:
- home city styling depends on theme/context token system
- rotating card visuals should not be hardcoded
- border/glow/icon treatments should come from theme + context styling

This is the correct sequencing.

---

# 19. Suggested File Format

JSON is perfectly acceptable, but TOML would also fit the SPF5000 style well.

A good first implementation choice is:
- JSON for easy browser/backend interoperability
- schema validation in backend
- loaded into frontend through API or generated static metadata

Either is acceptable.
The important part is:
- structured
- validated
- documented
- contributor-friendly

---

# 20. Acceptance Criteria

Theme system design is successful when:

- theme scope is clearly defined
- semantic token system is established
- contextual accents are separated from global theming
- alert safety rules are documented
- theme storage model is defined
- initial built-in theme strategy is clear
- home city styling is supported as a contextual accent system

---

# 21. Summary

SPF5000 should implement a real theme system, not just ad hoc styling.

Core principles:
- semantic tokens
- global theme + contextual accent layers
- shared admin/display styling
- protected emergency readability
- user/contributor theme support
- home city accent as a configurable context style

This system will support current and future features cleanly, especially:
- multi-city weather
- boot/loading states
- dynamic background coloring
- alert UI
- family personalization
