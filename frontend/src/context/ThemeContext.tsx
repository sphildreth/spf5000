import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'

import { getThemes } from '../api/themes'
import type { ThemeDefinition } from '../api/types'

const FALLBACK_THEMES: ThemeDefinition[] = [
  {
    id: 'default-dark',
    name: 'Default Dark',
    description: 'The original SPF5000 dark palette.',
    version: '1.0.0',
    mode: 'dark',
    tokens: {
      colors: {
        background_primary: '#0f1116',
        background_secondary: '#11151d',
        surface_default: '#171b24',
        surface_elevated: '#202635',
        surface_overlay: 'rgba(15, 17, 22, 0.92)',
        text_primary: '#f5f7fb',
        text_secondary: '#a4b0c2',
        border_default: 'rgba(148, 163, 184, 0.18)',
        accent_primary: '#80aefb',
        accent_secondary: '#4c8bf7',
        status_success: '#6ed9a1',
        status_warning: '#f6d06a',
        status_error: '#ff8d8d',
        display_overlay_text: 'rgba(249, 251, 255, 0.98)',
        glow_color: 'rgba(71, 214, 255, 0.26)',
        overlay_backdrop: 'rgba(8, 10, 14, 0.82)',
      },
      typography: {
        font_family_base: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        font_family_display: 'Orbitron, Rajdhani, Arial, sans-serif',
      },
      spacing: {},
      motion: {},
      shape: {
        shadow_card: '0 20px 40px rgba(0, 0, 0, 0.24)',
      },
    },
    components: {},
    contexts: {
      home_city_accent: {
        style: 'default',
        highlight_color: '#80aefb',
      },
    },
  },
  {
    id: 'retro-neon',
    name: 'Retro Neon',
    description: 'High-contrast cyan/green neon on near-black.',
    version: '1.0.0',
    mode: 'dark',
    tokens: {
      colors: {
        background_primary: '#080c0e',
        background_secondary: '#060a0c',
        surface_default: '#0d1417',
        surface_elevated: '#142229',
        surface_overlay: 'rgba(4, 14, 16, 0.82)',
        text_primary: '#e0f8f8',
        text_secondary: '#5dbcb8',
        border_default: 'rgba(0, 229, 200, 0.22)',
        accent_primary: '#00e5c8',
        accent_secondary: '#00b89e',
        status_success: '#39ffc0',
        status_warning: '#ffe04b',
        status_error: '#ff4f6a',
        display_overlay_text: 'rgba(224, 248, 248, 0.96)',
        glow_color: 'rgba(0, 229, 200, 0.32)',
        overlay_backdrop: 'rgba(4, 10, 12, 0.86)',
      },
      typography: {
        font_family_base: "'Share Tech Mono', 'Courier New', monospace",
        font_family_display: "'Orbitron', 'Share Tech Mono', monospace",
      },
      spacing: {},
      motion: {},
      shape: {
        shadow_card: '0 20px 40px rgba(0, 0, 0, 0.48)',
      },
    },
    components: {},
    contexts: {
      home_city_accent: {
        style: 'accent_glow',
        highlight_color: '#00ffcc',
      },
    },
  },
  {
    id: 'purple-dream',
    name: 'Purple Dream',
    description: 'Soft purple and violet with a deep indigo base.',
    version: '1.0.0',
    mode: 'dark',
    tokens: {
      colors: {
        background_primary: '#100d1a',
        background_secondary: '#0d0b17',
        surface_default: '#1a1628',
        surface_elevated: '#241f38',
        surface_overlay: 'rgba(10, 8, 22, 0.78)',
        text_primary: '#f0ecff',
        text_secondary: '#9d8fc8',
        border_default: 'rgba(167, 139, 250, 0.2)',
        accent_primary: '#c084fc',
        accent_secondary: '#a855f7',
        status_success: '#86efac',
        status_warning: '#fbbf24',
        status_error: '#f87171',
        display_overlay_text: 'rgba(240, 236, 255, 0.96)',
        glow_color: 'rgba(192, 132, 252, 0.3)',
        overlay_backdrop: 'rgba(10, 8, 22, 0.84)',
      },
      typography: {
        font_family_base: "'Nunito', 'Inter', system-ui, sans-serif",
        font_family_display: "'Nunito', 'Inter', system-ui, sans-serif",
      },
      spacing: {},
      motion: {},
      shape: {
        shadow_card: '0 20px 40px rgba(0, 0, 0, 0.36)',
      },
    },
    components: {},
    contexts: {
      home_city_accent: {
        style: 'accent_glow',
        highlight_color: '#c084fc',
      },
    },
  },
  {
    id: 'warm-family',
    name: 'Warm Family',
    description: 'Amber and walnut tones for a cosy living-room feel.',
    version: '1.0.0',
    mode: 'dark',
    tokens: {
      colors: {
        background_primary: '#13100b',
        background_secondary: '#0f0d09',
        surface_default: '#1e1912',
        surface_elevated: '#2a2217',
        surface_overlay: 'rgba(18, 14, 8, 0.8)',
        text_primary: '#fdf6e3',
        text_secondary: '#b8a07a',
        border_default: 'rgba(234, 179, 8, 0.2)',
        accent_primary: '#f59e0b',
        accent_secondary: '#d97706',
        status_success: '#a3e635',
        status_warning: '#fb923c',
        status_error: '#f87171',
        display_overlay_text: 'rgba(253, 246, 227, 0.96)',
        glow_color: 'rgba(245, 158, 11, 0.28)',
        overlay_backdrop: 'rgba(18, 14, 8, 0.86)',
      },
      typography: {
        font_family_base: "'Lato', 'Georgia', serif",
        font_family_display: "'Playfair Display', 'Georgia', serif",
      },
      spacing: {},
      motion: {},
      shape: {
        shadow_card: '0 20px 40px rgba(0, 0, 0, 0.28)',
      },
    },
    components: {},
    contexts: {
      home_city_accent: {
        style: 'solid_border',
        highlight_color: '#f5c842',
      },
    },
  },
]

export const HOME_CITY_ACCENT_STYLE_OPTIONS: ReadonlyArray<{
  value: string
  label: string
  description: string
}> = [
  { value: 'default', label: 'Default', description: 'Use the theme’s default home-city treatment.' },
  { value: 'subtle_border', label: 'Subtle border', description: 'A quiet accent treatment for the home city.' },
  { value: 'solid_border', label: 'Solid border', description: 'A stronger framed treatment for the home city.' },
  { value: 'house_icon', label: 'House icon', description: 'Use the home-city highlight color with a home-marker treatment.' },
  { value: 'accent_glow', label: 'Accent glow', description: 'Use a more vivid glow-forward highlight.' },
  { value: 'gradient_border', label: 'Gradient border', description: 'Use a richer accent treatment driven by the theme palette.' },
  { value: 'rainbow_gradient_border', label: 'Rainbow gradient border', description: 'Use the most playful accent treatment available.' },
]

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function pickToken(tokens: Record<string, string> | undefined, ...keys: string[]): string | undefined {
  for (const key of keys) {
    const value = tokens?.[key]
    if (typeof value === 'string' && value.trim().length > 0) {
      return value
    }
  }
  return undefined
}

function getHomeCityContext(theme: ThemeDefinition): Record<string, unknown> | null {
  const context = theme.contexts.home_city_accent
  return isRecord(context) ? context : null
}

function resolveHomeCityAccent(theme: ThemeDefinition, accentStyle: string): string | undefined {
  const colors = theme.tokens.colors
  const context = getHomeCityContext(theme)
  const contextStyle = typeof context?.style === 'string' ? context.style : undefined
  const highlightColor = typeof context?.highlight_color === 'string' ? context.highlight_color : undefined

  if (accentStyle === 'default') {
    return highlightColor ?? pickToken(colors, 'accent_primary', 'accent_secondary')
  }

  if (contextStyle === accentStyle && highlightColor) {
    return highlightColor
  }

  switch (accentStyle) {
    case 'subtle_border':
      return pickToken(colors, 'border_default', 'text_secondary', 'accent_primary')
    case 'solid_border':
      return pickToken(colors, 'accent_primary', 'border_default')
    case 'house_icon':
      return highlightColor ?? pickToken(colors, 'accent_primary', 'accent_secondary')
    case 'accent_glow':
      return highlightColor ?? pickToken(colors, 'accent_secondary', 'accent_primary')
    case 'gradient_border':
      return pickToken(colors, 'accent_secondary', 'accent_primary', 'status_warning')
    case 'rainbow_gradient_border':
      return pickToken(colors, 'accent_secondary', 'status_warning', 'accent_primary')
    default:
      return pickToken(colors, 'accent_primary')
  }
}

function applyThemeToRoot(theme: ThemeDefinition, accentStyle: string): void {
  const root = document.documentElement
  const colors = theme.tokens.colors
  const typography = theme.tokens.typography
  const shape = theme.tokens.shape

  const setToken = (name: string, value: string | undefined) => {
    if (value && value.trim().length > 0) {
      root.style.setProperty(name, value)
    } else {
      root.style.removeProperty(name)
    }
  }

  setToken('--bg', pickToken(colors, 'background_primary'))
  setToken('--panel', pickToken(colors, 'surface_default', 'background_secondary', 'background_primary'))
  setToken('--panel-strong', pickToken(colors, 'surface_elevated', 'background_elevated', 'surface_hover', 'background_secondary'))
  setToken('--panel-soft', pickToken(colors, 'surface_overlay', 'background_overlay', 'background_secondary'))
  setToken('--border', pickToken(colors, 'border_default', 'border_strong'))
  setToken('--text', pickToken(colors, 'text_primary'))
  setToken('--muted', pickToken(colors, 'text_muted', 'text_secondary'))
  setToken('--accent', pickToken(colors, 'accent_primary'))
  setToken('--accent-strong', pickToken(colors, 'accent_secondary', 'accent_primary_hover', 'accent_primary'))
  setToken('--ok', pickToken(colors, 'status_success', 'accent_success'))
  setToken('--warning', pickToken(colors, 'status_warning', 'accent_warning'))
  setToken('--danger', pickToken(colors, 'status_error', 'accent_danger'))
  setToken('--shadow', pickToken(shape, 'shadow_card', 'shadow_overlay'))

  setToken('--weather-bg', pickToken(colors, 'surface_overlay', 'background_overlay', 'overlay_backdrop'))
  setToken('--weather-border', pickToken(colors, 'border_default', 'border_strong'))
  setToken('--weather-text', pickToken(colors, 'display_overlay_text', 'text_primary'))
  setToken('--weather-text-muted', pickToken(colors, 'text_secondary', 'text_muted'))
  setToken('--boot-glow-default', pickToken(shape, 'glow_accent', 'glow_logo') ?? pickToken(colors, 'glow_color', 'accent_primary'))
  setToken('--boot-glow-empty', pickToken(colors, 'status_success', 'accent_success', 'glow_color'))
  setToken('--boot-glow-error', pickToken(colors, 'status_error', 'accent_danger', 'glow_color'))
  setToken('--idle-bg', pickToken(colors, 'surface_overlay', 'background_overlay', 'overlay_backdrop'))
  setToken('--idle-border', pickToken(colors, 'border_default', 'border_strong'))
  setToken('--font-family-base', pickToken(typography, 'font_family_base'))
  setToken('--font-family-display', pickToken(typography, 'font_family_display', 'font_family_base'))
  setToken('--accent-home-city', resolveHomeCityAccent(theme, accentStyle))

  root.dataset.themeId = theme.id
  root.dataset.themeMode = theme.mode
  root.dataset.homeCityAccentStyle = accentStyle
}

function mergeThemes(serverThemes: ThemeDefinition[]): ThemeDefinition[] {
  const serverIds = new Set(serverThemes.map((theme) => theme.id))
  return [...FALLBACK_THEMES.filter((theme) => !serverIds.has(theme.id)), ...serverThemes]
}

interface ThemeContextValue {
  themes: ThemeDefinition[]
  activeThemeId: string
  homeCityAccentStyle: string
  applyTheme: (id: string) => void
  applyHomeCityAccentStyle: (style: string) => void
  applyThemeSettings: (themeId: string, homeCityAccentStyle: string) => void
  refreshThemes: () => Promise<void>
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

const DEFAULT_THEME_ID = 'default-dark'
const DEFAULT_ACCENT_STYLE = 'default'

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [themes, setThemes] = useState<ThemeDefinition[]>(FALLBACK_THEMES)
  const [activeThemeId, setActiveThemeId] = useState<string>(DEFAULT_THEME_ID)
  const [homeCityAccentStyle, setHomeCityAccentStyle] = useState<string>(DEFAULT_ACCENT_STYLE)

  const applyById = useCallback((themeId: string, accentStyle: string, themeList: ThemeDefinition[]) => {
    const theme = themeList.find((item) => item.id === themeId) ?? themeList[0]
    if (theme) {
      applyThemeToRoot(theme, accentStyle)
    }
  }, [])

  const refreshThemes = useCallback(async () => {
    try {
      const response = await getThemes({ force: true })
      const mergedThemes = mergeThemes(response.themes)
      const nextThemeId = response.active_theme_id || DEFAULT_THEME_ID
      const nextAccentStyle = response.home_city_accent_style || DEFAULT_ACCENT_STYLE

      setThemes(mergedThemes)
      setActiveThemeId(nextThemeId)
      setHomeCityAccentStyle(nextAccentStyle)
      applyById(nextThemeId, nextAccentStyle, mergedThemes)
    } catch {
      applyById(activeThemeId, homeCityAccentStyle, themes)
    }
  }, [activeThemeId, applyById, homeCityAccentStyle, themes])

  useEffect(() => {
    let cancelled = false

    void (async () => {
      try {
        const response = await getThemes()
        if (cancelled) {
          return
        }
        const mergedThemes = mergeThemes(response.themes)
        const nextThemeId = response.active_theme_id || DEFAULT_THEME_ID
        const nextAccentStyle = response.home_city_accent_style || DEFAULT_ACCENT_STYLE

        setThemes(mergedThemes)
        setActiveThemeId(nextThemeId)
        setHomeCityAccentStyle(nextAccentStyle)
        applyById(nextThemeId, nextAccentStyle, mergedThemes)
      } catch {
        if (!cancelled) {
          applyById(DEFAULT_THEME_ID, DEFAULT_ACCENT_STYLE, FALLBACK_THEMES)
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [applyById])

  const applyTheme = useCallback(
    (themeId: string) => {
      setActiveThemeId(themeId)
      applyById(themeId, homeCityAccentStyle, themes)
    },
    [applyById, homeCityAccentStyle, themes],
  )

  const applyHomeCityAccentStyleFn = useCallback(
    (accentStyle: string) => {
      setHomeCityAccentStyle(accentStyle)
      applyById(activeThemeId, accentStyle, themes)
    },
    [activeThemeId, applyById, themes],
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

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
