import { apiGet, apiPut } from './http'
import {
  asBackgroundFillMode,
  asBoolean,
  asDisplayTransitionMode,
  asFitMode,
  asNumber,
  asRecord,
  asString,
  asStringArray,
  type FrameSettings,
  type SettingsTimeReference,
  type SleepSchedule,
  type SleepScheduleUpdateRequest,
} from './types'

export async function getSettings(): Promise<FrameSettings> {
  const payload = await apiGet<unknown>('/api/settings')
  return normalizeSettings(payload)
}

export async function updateSettings(settings: FrameSettings): Promise<FrameSettings> {
  const payload = await apiPut<FrameSettings, unknown>('/api/settings', settings)
  return normalizeSettings(payload)
}

export async function getSleepSchedule(): Promise<SleepSchedule> {
  const payload = await apiGet<unknown>('/api/settings/sleep-schedule')
  return normalizeSleepSchedule(payload)
}

export async function updateSleepSchedule(request: SleepScheduleUpdateRequest): Promise<SleepSchedule> {
  const payload = await apiPut<SleepScheduleUpdateRequest, unknown>('/api/settings/sleep-schedule', request)
  return normalizeSleepSchedule(payload)
}

export async function getSettingsTimeReference(): Promise<SettingsTimeReference> {
  const payload = await apiGet<unknown>('/api/settings/time-reference')
  return normalizeSettingsTimeReference(payload)
}

export function normalizeSleepSchedule(payload: unknown): SleepSchedule {
  const record = asRecord(payload)
  return {
    sleep_schedule_enabled: asBoolean(record?.sleep_schedule_enabled, false),
    sleep_start_local_time: asString(record?.sleep_start_local_time, '22:00'),
    sleep_end_local_time: asString(record?.sleep_end_local_time, '08:00'),
    display_timezone: normalizeDisplayTimezone(record?.display_timezone),
  }
}

function normalizeSettingsTimeReference(payload: unknown): SettingsTimeReference {
  const record = asRecord(payload)
  const piLocalTimezone = asString(record?.pi_local_timezone, 'UTC')

  return {
    current_server_utc_timestamp: asString(record?.current_server_utc_timestamp, ''),
    pi_local_timezone: piLocalTimezone,
    configured_display_timezone: normalizeDisplayTimezone(record?.configured_display_timezone),
    effective_display_timezone: asString(record?.effective_display_timezone, piLocalTimezone),
    available_timezones: asStringArray(record?.available_timezones),
  }
}

function normalizeDisplayTimezone(value: unknown): string | null {
  const normalized = asString(value, '').trim()
  return normalized.length > 0 ? normalized : null
}

function normalizeSettings(payload: unknown): FrameSettings {
  const record = asRecord(payload)

  return {
    frame_name: asString(record?.frame_name, 'SPF5000'),
    display_variant_width: asNumber(record?.display_variant_width, 1920),
    display_variant_height: asNumber(record?.display_variant_height, 1080),
    thumbnail_max_size: asNumber(record?.thumbnail_max_size, 400),
    theme_id: asString(record?.theme_id, 'default-dark'),
    home_city_accent_style: asString(record?.home_city_accent_style, 'default'),
    slideshow_interval_seconds: asNumber(record?.slideshow_interval_seconds, 30),
    transition_mode: asDisplayTransitionMode(record?.transition_mode, 'slide'),
    transition_duration_ms: asNumber(record?.transition_duration_ms, 700),
    fit_mode: asFitMode(record?.fit_mode, 'contain'),
    shuffle_enabled: asBoolean(record?.shuffle_enabled, true),
    shuffle_bag_enabled: asBoolean(record?.shuffle_bag_enabled, false),
    selected_collection_id: asString(record?.selected_collection_id, 'default-collection'),
    active_display_profile_id: asString(record?.active_display_profile_id, 'default-display-profile'),
    background_fill_mode: asBackgroundFillMode(record?.background_fill_mode, 'black'),
  }
}
