/**
 * ThemeContext – first-pass theme system scaffold.
 *
 * Fetches /api/themes on mount; falls back to built-in definitions if the
 * backend endpoint is not yet available.  Applies active-theme tokens as CSS
 * custom properties on document.documentElement so every CSS rule that
 * references var(--accent) etc. picks up the right values automatically.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'

import { getThemes } from '../api/themes'
import type { ThemeDefinition, ThemeTokens } from '../api/types'

// ─── Built-in theme catalogue ─────────────────────────────────────────────

const BUILTIN_THEMES: ThemeDefinition[] = [
  {
    id: 'default-dark',
    label: 'Default Dark',
    description: 'The original SPF5000 dark palette.',
    tokens: {
      bg: '#0f1116',
      panel: '#171b24',
      panelStrong: '#202635',
      panelSoft: '#11151d',
      border: 'rgba(148, 163, 184, 0.18)',
      text: '#f5f7fb',
      muted: '#a4b0c2',
      accent: '#80aefb',
      accentStrong: '#4c8bf7',
      ok: '#6ed9a1',
      warning: '#f6d06a',
      danger: '#ff8d8d',
      shadow: '0 20px 40px rgba(0, 0, 0, 0.24)',
      weatherBg: 'rgba(12, 16, 24, 0.74)',
      weatherBorder: 'rgba(255, 255, 255, 0.14)',
      weatherText: 'rgba(249, 251, 255, 0.98)',
      weatherTextMuted: 'rgba(182, 199, 224, 0.82)',
      bootGlowDefault: 'rgba(71, 214, 255, 0.26)',
      bootGlowEmpty: 'rgba(132, 240, 206, 0.22)',
      bootGlowError: 'rgba(255, 101, 184, 0.26)',
      idleBg: 'rgba(8, 10, 14, 0.82)',
      idleBorder: 'rgba(148, 163, 184, 0.14)',
    },
  },
  {
    id: 'retro-neon',
    label: 'Retro Neon',
    description: 'High-contrast cyan/green neon on near-black.',
    tokens: {
      bg: '#080c0e',
      panel: '#0d1417',
      panelStrong: '#142229',
      panelSoft: '#060a0c',
      border: 'rgba(0, 229, 200, 0.22)',
      text: '#e0f8f8',
      muted: '#5dbcb8',
      accent: '#00e5c8',
      accentStrong: '#00b89e',
      ok: '#39ffc0',
      warning: '#ffe04b',
      danger: '#ff4f6a',
      shadow: '0 20px 40px rgba(0, 0, 0, 0.48)',
      weatherBg: 'rgba(4, 14, 16, 0.82)',
      weatherBorder: 'rgba(0, 229, 200, 0.28)',
      weatherText: 'rgba(224, 248, 248, 0.96)',
      weatherTextMuted: 'rgba(93, 188, 184, 0.9)',
      bootGlowDefault: 'rgba(0, 229, 200, 0.32)',
      bootGlowEmpty: 'rgba(57, 255, 192, 0.28)',
      bootGlowError: 'rgba(255, 79, 106, 0.32)',
      idleBg: 'rgba(4, 10, 12, 0.86)',
      idleBorder: 'rgba(0, 229, 200, 0.2)',
    },
  },
  {
    id: 'purple-dream',
    label: 'Purple Dream',
    description: 'Soft purple and violet with a deep indigo base.',
    tokens: {
      bg: '#100d1a',
      panel: '#1a1628',
      panelStrong: '#241f38',
      panelSoft: '#0d0b17',
      border: 'rgba(167, 139, 250, 0.2)',
      text: '#f0ecff',
      muted: '#9d8fc8',
      accent: '#c084fc',
      accentStrong: '#a855f7',
      ok: '#86efac',
      warning: '#fbbf24',
      danger: '#f87171',
      shadow: '0 20px 40px rgba(0, 0, 0, 0.36)',
      weatherBg: 'rgba(10, 8, 22, 0.78)',
      weatherBorder: 'rgba(167, 139, 250, 0.22)',
      weatherText: 'rgba(240, 236, 255, 0.96)',
      weatherTextMuted: 'rgba(157, 143, 200, 0.9)',
      bootGlowDefault: 'rgba(192, 132, 252, 0.3)',
      bootGlowEmpty: 'rgba(134, 239, 172, 0.24)',
      bootGlowError: 'rgba(248, 113, 113, 0.3)',
      idleBg: 'rgba(10, 8, 22, 0.84)',
      idleBorder: 'rgba(167, 139, 250, 0.16)',
    },
  },
  {
    id: 'warm-family',
    label: 'Warm Family',
    description: 'Amber and walnut tones for a cosy living-room feel.',
    tokens: {
      bg: '#13100b',
      panel: '#1e1912',
      panelStrong: '#2a2217',
      panelSoft: '#0f0d09',
      border: 'rgba(234, 179, 8, 0.2)',
      text: '#fdf6e3',
      muted: '#b8a07a',
      accent: '#f59e0b',
      accentStrong: '#d97706',
      ok: '#a3e635',
      warning: '#fb923c',
      danger: '#f87171',
      shadow: '0 20px 40px rgba(0, 0, 0, 0.28)',
      weatherBg: 'rgba(18, 14, 8, 0.8)',
      weatherBorder: 'rgba(234, 179, 8, 0.2)',
      weatherText: 'rgba(253, 246, 227, 0.96)',
      weatherTextMuted: 'rgba(184, 160, 122, 0.9)',
      bootGlowDefault: 'rgba(245, 158, 11, 0.28)',
      bootGlowEmpty: 'rgba(163, 230, 53, 0.22)',
      bootGlowError: 'rgba(248, 113, 113, 0.28)',
      idleBg: 'rgba(18, 14, 8, 0.86)',
      idleBorder: 'rgba(234, 179, 8, 0.16)',
    },
  },
]

// ─── Home-city accent style catalogue ─────────────────────────────────────

export const HOME_CITY_ACCENT_STYLE_OPTIONS: ReadonlyArray<{
  value: string
  label: string
  description: string
}> = [
  { value: 'default', label: 'Default', description: 'Matches the active theme accent colour.' },
  { value: 'vivid', label: 'Vivid', description: 'Brighter saturated accent for the city label.' },
  { value: 'warm', label: 'Warm', description: 'Amber-warm tint regardless of theme.' },
  { value: 'cool', label: 'Cool', description: 'Ice-blue tint regardless of theme.' },
  { value: 'neutral', label: 'Neutral', description: 'Soft white, blends quietly.' },
]

const HOME_CITY_ACCENT_COLORS: Record<string, string> = {
  default: '',            // resolved at apply time → var(--accent)
  vivid: '#ffe066',
  warm: '#f59e0b',
  cool: '#67e8f9',
  neutral: 'rgba(255, 255, 255, 0.72)',
}

// ─── CSS variable application ──────────────────────────────────────────────

/** Map a ThemeTokens object onto CSS custom properties of document.documentElement. */
function applyTokensToRoot(tokens: ThemeTokens, homeCityAccentStyle: string): void {
  const el = document.documentElement
  const set = (name: string, value: string | undefined) => {
    if (value !== undefined && value !== '') {
      el.style.setProperty(name, value)
    }
  }

  set('--bg', tokens.bg)
  set('--panel', tokens.panel)
  set('--panel-strong', tokens.panelStrong)
  set('--panel-soft', tokens.panelSoft)
  set('--border', tokens.border)
  set('--text', tokens.text)
  set('--muted', tokens.muted)
  set('--accent', tokens.accent)
  set('--accent-strong', tokens.accentStrong)
  set('--ok', tokens.ok)
  set('--warning', tokens.warning)
  set('--danger', tokens.danger)
  set('--shadow', tokens.shadow)

  // Display overlay surfaces – fall back to defaults baked into global.css if absent
  if (tokens.weatherBg) set('--weather-bg', tokens.weatherBg)
  if (tokens.weatherBorder) set('--weather-border', tokens.weatherBorder)
  if (tokens.weatherText) set('--weather-text', tokens.weatherText)
  if (tokens.weatherTextMuted) set('--weather-text-muted', tokens.weatherTextMuted)
  if (tokens.bootGlowDefault) set('--boot-glow-default', tokens.bootGlowDefault)
  if (tokens.bootGlowEmpty) set('--boot-glow-empty', tokens.bootGlowEmpty)
  if (tokens.bootGlowError) set('--boot-glow-error', tokens.bootGlowError)
  if (tokens.idleBg) set('--idle-bg', tokens.idleBg)
  if (tokens.idleBorder) set('--idle-border', tokens.idleBorder)

  // Home-city accent: explicit colour overrides or fall through to --accent
  const accentHomeCity =
    tokens.accentHomeCityColor ??
    HOME_CITY_ACCENT_COLORS[homeCityAccentStyle] ??
    ''
  if (accentHomeCity) {
    set('--accent-home-city', accentHomeCity)
  } else {
    // Reset to the CSS fallback (var(--accent)) by removing inline override
    el.style.removeProperty('--accent-home-city')
  }
}

// ─── Context definition ────────────────────────────────────────────────────

interface ThemeContextValue {
  themes: ThemeDefinition[]
  activeThemeId: string
  homeCityAccentStyle: string
  /** Immediately apply a theme by ID (also updates context state). */
  applyTheme: (id: string) => void
  /** Update home-city accent style and re-apply CSS vars. */
  applyHomeCityAccentStyle: (style: string) => void
  /** Apply both theme-related selections immediately without a page reload. */
  applyThemeSettings: (themeId: string, homeCityAccentStyle: string) => void
  /** Refresh theme definitions and active selection from /api/themes when available. */
  refreshThemes: () => Promise<void>
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

// ─── Provider ─────────────────────────────────────────────────────────────

const DEFAULT_THEME_ID = 'default-dark'
const DEFAULT_ACCENT_STYLE = 'default'

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [themes, setThemes] = useState<ThemeDefinition[]>(BUILTIN_THEMES)
  const [activeThemeId, setActiveThemeId] = useState<string>(DEFAULT_THEME_ID)
  const [homeCityAccentStyle, setHomeCityAccentStyle] = useState<string>(DEFAULT_ACCENT_STYLE)

  /** Apply a given theme ID and accent style to the document root. */
  const applyById = useCallback(
    (id: string, accentStyle: string, themeList: ThemeDefinition[]) => {
      const theme = themeList.find((t) => t.id === id) ?? themeList[0]
      if (theme) {
        applyTokensToRoot(theme.tokens, accentStyle)
      }
    },
    [],
  )

  const refreshThemes = useCallback(async () => {
    try {
      const response = await getThemes()

      // Merge built-ins with any server-defined themes (server wins on conflicts)
      const serverIds = new Set(response.themes.map((t) => t.id))
      const merged = [
        ...BUILTIN_THEMES.filter((t) => !serverIds.has(t.id)),
        ...response.themes,
      ]

      const nextThemeId = response.active_theme_id || DEFAULT_THEME_ID
      const nextAccentStyle = response.home_city_accent_style || DEFAULT_ACCENT_STYLE

      setThemes(merged)
      setActiveThemeId(nextThemeId)
      setHomeCityAccentStyle(nextAccentStyle)
      applyById(nextThemeId, nextAccentStyle, merged)
    } catch {
      // Backend doesn't have /api/themes yet – apply built-in defaults.
      applyById(activeThemeId, homeCityAccentStyle, themes)
    }
  }, [activeThemeId, applyById, homeCityAccentStyle, themes])

  // Bootstrap: attempt to load themes from API; silently fall back to built-ins.
  useEffect(() => {
    let cancelled = false

    void (async () => {
      try {
        const response = await getThemes()
        if (cancelled) {
          return
        }

        const serverIds = new Set(response.themes.map((t) => t.id))
        const merged = [
          ...BUILTIN_THEMES.filter((t) => !serverIds.has(t.id)),
          ...response.themes,
        ]

        const nextThemeId = response.active_theme_id || DEFAULT_THEME_ID
        const nextAccentStyle = response.home_city_accent_style || DEFAULT_ACCENT_STYLE

        setThemes(merged)
        setActiveThemeId(nextThemeId)
        setHomeCityAccentStyle(nextAccentStyle)
        applyById(nextThemeId, nextAccentStyle, merged)
      } catch {
        if (!cancelled) {
          applyById(DEFAULT_THEME_ID, DEFAULT_ACCENT_STYLE, BUILTIN_THEMES)
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [applyById])

  const applyTheme = useCallback(
    (id: string) => {
      setActiveThemeId(id)
      applyById(id, homeCityAccentStyle, themes)
    },
    [applyById, homeCityAccentStyle, themes],
  )

  const applyHomeCityAccentStyleFn = useCallback(
    (style: string) => {
      setHomeCityAccentStyle(style)
      applyById(activeThemeId, style, themes)
    },
    [applyById, activeThemeId, themes],
  )

  const applyThemeSettings = useCallback(
    (themeId: string, accentStyle: string) => {
      setActiveThemeId(themeId)
      setHomeCityAccentStyle(accentStyle)
      applyById(themeId, accentStyle, themes)
    },
    [applyById, themes],
  )

  return (
    <ThemeContext.Provider
      value={{
        themes,
        activeThemeId,
        homeCityAccentStyle,
        applyTheme,
        applyHomeCityAccentStyle: applyHomeCityAccentStyleFn,
        applyThemeSettings,
        refreshThemes,
      }}
    >
      {children}
    </ThemeContext.Provider>
  )
}

// ─── Hook ──────────────────────────────────────────────────────────────────

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext)
  if (!ctx) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return ctx
}
