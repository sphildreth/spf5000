import { apiGet, apiPut } from './http'
import { asBoolean, asFitMode, asNumber, asRecord, asString, type FrameSettings } from './types'

export async function getSettings(): Promise<FrameSettings> {
  const payload = await apiGet<unknown>('/api/settings')
  return normalizeSettings(payload)
}

export async function updateSettings(settings: FrameSettings): Promise<FrameSettings> {
  const payload = await apiPut<FrameSettings, unknown>('/api/settings', settings)
  return normalizeSettings(payload)
}

function normalizeSettings(payload: unknown): FrameSettings {
  const record = asRecord(payload)

  return {
    frame_name: asString(record?.frame_name, 'SPF5000'),
    display_variant_width: asNumber(record?.display_variant_width, 1920),
    display_variant_height: asNumber(record?.display_variant_height, 1080),
    thumbnail_max_size: asNumber(record?.thumbnail_max_size, 400),
    slideshow_interval_seconds: asNumber(record?.slideshow_interval_seconds, 30),
    transition_mode: asString(record?.transition_mode, 'slide'),
    transition_duration_ms: asNumber(record?.transition_duration_ms, 700),
    fit_mode: asFitMode(record?.fit_mode, 'contain'),
    shuffle_enabled: asBoolean(record?.shuffle_enabled, true),
    selected_collection_id: asString(record?.selected_collection_id, 'default-collection'),
    active_display_profile_id: asString(record?.active_display_profile_id, 'default-display-profile'),
  }
}
