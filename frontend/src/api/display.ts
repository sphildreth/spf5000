import { apiGet, apiPut } from './http'
import { asArray, asBoolean, asFitMode, asNumber, asOptionalString, asRecord, asString, type DisplayConfig, type DisplayConfigUpdateRequest, type DisplayPlaylist, type PlaylistItem } from './types'
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
    transition_mode: asString(record?.transition_mode, DEFAULT_DISPLAY_CONFIG.transition_mode),
    transition_duration_ms: asNumber(record?.transition_duration_ms, DEFAULT_DISPLAY_CONFIG.transition_duration_ms),
    fit_mode: asFitMode(record?.fit_mode, DEFAULT_DISPLAY_CONFIG.fit_mode),
    shuffle_enabled: asBoolean(record?.shuffle_enabled, DEFAULT_DISPLAY_CONFIG.shuffle_enabled),
    idle_message: asString(record?.idle_message, DEFAULT_DISPLAY_CONFIG.idle_message),
    refresh_interval_seconds: asNumber(record?.refresh_interval_seconds, DEFAULT_DISPLAY_CONFIG.refresh_interval_seconds),
    is_default: asBoolean(record?.is_default, DEFAULT_DISPLAY_CONFIG.is_default),
    created_at: asString(record?.created_at, DEFAULT_DISPLAY_CONFIG.created_at),
    updated_at: asString(record?.updated_at, DEFAULT_DISPLAY_CONFIG.updated_at),
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
  }
}
