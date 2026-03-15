import { apiGet, apiPut } from './http'
import {
  asArray,
  asFitMode,
  asNumber,
  asOptionalNumber,
  asOptionalPlaybackMode,
  asOptionalString,
  asPlaybackMode,
  asRecord,
  asString,
  type DisplayConfig,
  type DisplayConfigUpdateRequest,
  type DisplayPlaylist,
  type PlaylistItem,
} from './types'

const DEFAULT_DISPLAY_CONFIG: DisplayConfig = {
  interval_seconds: 30,
  transition_duration_ms: 1200,
  fit_mode: 'contain',
  playback_mode: 'sequential',
  transition_mode: 'slide',
  idle_message: 'Waiting for photos to arrive.',
  refresh_interval_seconds: 60,
}

export async function getDisplayConfig(): Promise<DisplayConfig> {
  const payload = await apiGet<unknown>('/api/display/config')
  return normalizeDisplayConfig(payload)
}

export async function updateDisplayConfig(
  request: DisplayConfigUpdateRequest,
): Promise<DisplayConfig> {
  const payload = await apiPut<DisplayConfigUpdateRequest, unknown>('/api/display/config', request)
  return normalizeDisplayConfig(payload)
}

export async function getDisplayPlaylist(): Promise<DisplayPlaylist> {
  const payload = await apiGet<unknown>('/api/display/playlist')
  const record = asRecord(payload)
  const itemsSource = Array.isArray(payload) ? payload : record?.items ?? record?.playlist ?? []

  return {
    items: asArray(itemsSource, normalizePlaylistItem).filter((item) => item.image_url.length > 0),
    revision: asOptionalString(record?.revision),
    playback_mode: asOptionalPlaybackMode(record?.playback_mode),
  }
}

export function getDefaultDisplayConfig(): DisplayConfig {
  return DEFAULT_DISPLAY_CONFIG
}

function normalizeDisplayConfig(payload: unknown): DisplayConfig {
  const record = asRecord(payload)

  return {
    interval_seconds: asNumber(record?.interval_seconds ?? record?.slideshow_interval_seconds, 30),
    transition_duration_ms: asNumber(record?.transition_duration_ms, 1200),
    fit_mode: asFitMode(record?.fit_mode, DEFAULT_DISPLAY_CONFIG.fit_mode),
    playback_mode: asPlaybackMode(
      record?.playback_mode ?? (record?.shuffle_enabled === true ? 'shuffle' : 'sequential'),
      DEFAULT_DISPLAY_CONFIG.playback_mode,
    ),
    transition_mode: asString(record?.transition_mode, 'slide'),
    idle_message: asString(record?.idle_message, DEFAULT_DISPLAY_CONFIG.idle_message),
    refresh_interval_seconds: asNumber(record?.refresh_interval_seconds, 60),
  }
}

function normalizePlaylistItem(item: unknown, index: number): PlaylistItem {
  const record = asRecord(item)

  return {
    id: asOptionalString(record?.id) ?? `${index}`,
    title:
      asOptionalString(record?.title) ??
      asOptionalString(record?.filename) ??
      asOptionalString(record?.name) ??
      `Photo ${index + 1}`,
    image_url:
      asOptionalString(record?.image_url) ??
      asOptionalString(record?.display_url) ??
      asOptionalString(record?.url) ??
      '',
    width: asOptionalNumber(record?.width),
    height: asOptionalNumber(record?.height),
    collection_name: asOptionalString(record?.collection_name),
    source_name: asOptionalString(record?.source_name),
  }
}
