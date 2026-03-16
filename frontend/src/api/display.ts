import { apiGet, apiPut } from './http'
import {
  asArray,
  asBackgroundFillMode,
  asBoolean,
  asDisplayTransitionMode,
  asFitMode,
  asNumber,
  asOptionalString,
  asRecord,
  asString,
  asStringArray,
  type BackgroundFillMode,
  type DisplayConfig,
  type DisplayConfigUpdateRequest,
  type DisplayPlaylist,
  type PlaylistItem,
  type PlaylistItemBackground,
} from './types'
import { normalizeSleepSchedule } from './settings'

const DEFAULT_DISPLAY_CONFIG: DisplayConfig = {
  id: 'default-display-profile',
  name: 'Default Display',
  selected_collection_id: 'default-collection',
  slideshow_interval_seconds: 30,
  transition_mode: 'slide',
  transition_duration_ms: 700,
  fit_mode: 'contain',
  shuffle_enabled: true,
  idle_message: 'Add photos from the admin UI to begin playback.',
  refresh_interval_seconds: 60,
  background_fill_mode: 'black',
  is_default: true,
  created_at: '',
  updated_at: '',
}

export async function getDisplayConfig(): Promise<DisplayConfig> {
  const payload = await apiGet<unknown>('/api/display/config')
  return normalizeDisplayConfig(payload)
}

export async function updateDisplayConfig(request: DisplayConfigUpdateRequest): Promise<DisplayConfig> {
  const payload = await apiPut<DisplayConfigUpdateRequest, unknown>('/api/display/config', request)
  return normalizeDisplayConfig(payload)
}

export async function getDisplayPlaylist(): Promise<DisplayPlaylist> {
  const payload = await apiGet<unknown>('/api/display/playlist')
  const record = asRecord(payload)

  return {
    collection_id: asOptionalString(record?.collection_id) ?? null,
    collection_name: asOptionalString(record?.collection_name) ?? null,
    shuffle_enabled: asBoolean(record?.shuffle_enabled, DEFAULT_DISPLAY_CONFIG.shuffle_enabled),
    playlist_revision: asString(record?.playlist_revision, 'empty'),
    profile: record?.profile ? normalizeDisplayConfig(record.profile) : DEFAULT_DISPLAY_CONFIG,
    items: asArray(record?.items, normalizePlaylistItem).filter((item) => item.display_url.length > 0),
    sleep_schedule: record?.sleep_schedule ? normalizeSleepSchedule(record.sleep_schedule) : null,
  }
}

export function getDefaultDisplayConfig(): DisplayConfig {
  return DEFAULT_DISPLAY_CONFIG
}

function normalizeDisplayConfig(payload: unknown): DisplayConfig {
  const record = asRecord(payload)

  return {
    id: asString(record?.id, DEFAULT_DISPLAY_CONFIG.id),
    name: asString(record?.name, DEFAULT_DISPLAY_CONFIG.name),
    selected_collection_id: asOptionalString(record?.selected_collection_id) ?? null,
    slideshow_interval_seconds: asNumber(record?.slideshow_interval_seconds, DEFAULT_DISPLAY_CONFIG.slideshow_interval_seconds),
    transition_mode: asDisplayTransitionMode(record?.transition_mode, DEFAULT_DISPLAY_CONFIG.transition_mode),
    transition_duration_ms: asNumber(record?.transition_duration_ms, DEFAULT_DISPLAY_CONFIG.transition_duration_ms),
    fit_mode: asFitMode(record?.fit_mode, DEFAULT_DISPLAY_CONFIG.fit_mode),
    shuffle_enabled: asBoolean(record?.shuffle_enabled, DEFAULT_DISPLAY_CONFIG.shuffle_enabled),
    idle_message: asString(record?.idle_message, DEFAULT_DISPLAY_CONFIG.idle_message),
    refresh_interval_seconds: asNumber(record?.refresh_interval_seconds, DEFAULT_DISPLAY_CONFIG.refresh_interval_seconds),
    background_fill_mode: asBackgroundFillMode(record?.background_fill_mode, DEFAULT_DISPLAY_CONFIG.background_fill_mode),
    is_default: asBoolean(record?.is_default, DEFAULT_DISPLAY_CONFIG.is_default),
    created_at: asString(record?.created_at, DEFAULT_DISPLAY_CONFIG.created_at),
    updated_at: asString(record?.updated_at, DEFAULT_DISPLAY_CONFIG.updated_at),
  }
}

function normalizePlaylistItemBackground(value: unknown): PlaylistItemBackground | null {
  const record = asRecord(value)
  if (!record) {
    return null
  }

  return {
    ready: asBoolean(record.ready, false),
    dominant_color: asOptionalString(record.dominant_color) ?? null,
    gradient_colors: Array.isArray(record.gradient_colors) ? asStringArray(record.gradient_colors) : null,
  }
}

function normalizePlaylistItem(item: unknown, index: number): PlaylistItem {
  const record = asRecord(item)

  return {
    asset_id: asString(record?.asset_id ?? record?.id, `${index}`),
    filename: asString(record?.filename, `Photo ${index + 1}`),
    display_url: asString(record?.display_url ?? record?.image_url ?? record?.url, ''),
    thumbnail_url: asString(record?.thumbnail_url, ''),
    width: asNumber(record?.width, 0),
    height: asNumber(record?.height, 0),
    checksum_sha256: asString(record?.checksum_sha256, ''),
    mime_type: asString(record?.mime_type, 'image/jpeg'),
    collection_name: asOptionalString(record?.collection_name),
    source_name: asOptionalString(record?.source_name),
    background: normalizePlaylistItemBackground(record?.background),
  }
}

export function buildBackgroundStyle(
  mode: BackgroundFillMode,
  background: PlaylistItemBackground | null | undefined,
): string {
  if (mode === 'black' || !background?.ready) {
    return '#000'
  }

  if (mode === 'palette_wash') {
    const palette = getBackgroundPalette(background)
    if (palette.length >= 3) {
      return [
        `radial-gradient(circle at 18% 24%, ${withAlpha(palette[0], 0.34)} 0%, transparent 50%)`,
        `radial-gradient(circle at 82% 20%, ${withAlpha(palette[1], 0.3)} 0%, transparent 46%)`,
        `radial-gradient(circle at 50% 78%, ${withAlpha(palette[2], 0.28)} 0%, transparent 52%)`,
        `linear-gradient(145deg, ${withAlpha(palette[0], 0.54)}, ${withAlpha(palette[1], 0.42)}, ${withAlpha(palette[2], 0.48)})`,
      ].join(', ')
    }
  }

  if (
    mode === 'gradient' ||
    mode === 'blurred_backdrop' ||
    mode === 'mirrored_edges' ||
    mode === 'soft_vignette' ||
    mode === 'adaptive_auto'
  ) {
    const colors = background.gradient_colors
    if (colors && colors.length >= 2) {
      return `linear-gradient(135deg, ${colors.join(', ')})`
    }
    return background.dominant_color ?? '#000'
  }

  return background.dominant_color ?? '#000'
}

function getBackgroundPalette(background: PlaylistItemBackground): string[] {
  const colors = background.gradient_colors?.filter((color) => color.length > 0) ?? []
  const dominant = background.dominant_color

  if (colors.length >= 3) {
    return colors.slice(0, 3)
  }

  if (colors.length === 2 && dominant) {
    return [colors[0], colors[1], dominant]
  }

  if (colors.length === 1 && dominant) {
    return [colors[0], dominant, dominant]
  }

  if (dominant) {
    return [dominant, dominant, dominant]
  }

  return colors
}

function withAlpha(color: string, alpha: number): string {
  const normalized = color.trim()
  if (normalized.startsWith('#')) {
    const hex = normalized.slice(1)
    const expanded = hex.length === 3 ? hex.split('').map((value) => value + value).join('') : hex
    if (expanded.length === 6) {
      const red = Number.parseInt(expanded.slice(0, 2), 16)
      const green = Number.parseInt(expanded.slice(2, 4), 16)
      const blue = Number.parseInt(expanded.slice(4, 6), 16)
      if ([red, green, blue].every(Number.isFinite)) {
        return `rgba(${red}, ${green}, ${blue}, ${alpha})`
      }
    }
  }

  return normalized
}
