import { apiGet, apiPut } from './http'
import { asBoolean, asFitMode, asRecord, asString, type FrameSettings } from './types'

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
    slideshow_interval_seconds:
      typeof record?.slideshow_interval_seconds === 'number' ? record.slideshow_interval_seconds : 30,
    transition_mode: asString(record?.transition_mode, 'slide'),
    fit_mode: asFitMode(record?.fit_mode, 'contain'),
    shuffle_enabled: asBoolean(record?.shuffle_enabled, false),
  }
}
