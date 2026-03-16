import { apiGet, apiPostEmpty, apiPut } from './http'
import {
  asArray,
  asBoolean,
  asNumber,
  asOptionalNumber,
  asOptionalString,
  asRecord,
  asString,
  type DisplayAlerts,
  type DisplayAlertPresentation,
  type DisplayWeather,
  type WeatherAlert,
  type WeatherAlertsState,
  type WeatherCurrentConditions,
  type WeatherLocation,
  type WeatherProviderState,
  type WeatherRefreshRun,
  type WeatherSettings,
  type WeatherStatus,
} from './types'

export async function getWeatherSettings(): Promise<WeatherSettings> {
  const payload = await apiGet<unknown>('/api/weather/settings')
  return normalizeWeatherSettings(payload)
}

export async function updateWeatherSettings(settings: WeatherSettings): Promise<WeatherSettings> {
  const payload = await apiPut<WeatherSettings, unknown>('/api/weather/settings', settings)
  return normalizeWeatherSettings(payload)
}

export async function getWeatherStatus(): Promise<WeatherStatus> {
  const payload = await apiGet<unknown>('/api/weather/status')
  const record = asRecord(payload)

  return {
    provider_status: normalizeWeatherProviderState(record?.provider_status),
    current_conditions: record?.current_conditions ? normalizeWeatherCurrentConditions(record.current_conditions) : null,
    dominant_alert: record?.dominant_alert ? normalizeWeatherAlert(record.dominant_alert) : null,
    active_alert_count: asNumber(record?.active_alert_count, 0),
    current_display_action: asString(record?.current_display_action, 'none'),
    recent_refresh_runs: asArray(record?.recent_refresh_runs, (item) => normalizeWeatherRefreshRun(item)),
  }
}

export async function getWeatherAlerts(): Promise<WeatherAlertsState> {
  const payload = await apiGet<unknown>('/api/weather/alerts')
  const record = asRecord(payload)

  return {
    provider_status: normalizeWeatherProviderState(record?.provider_status),
    alert_count: asNumber(record?.alert_count, 0),
    dominant_alert: record?.dominant_alert ? normalizeWeatherAlert(record.dominant_alert) : null,
    active_alerts: asArray(record?.active_alerts, (item) => normalizeWeatherAlert(item)),
  }
}

export async function refreshWeather(): Promise<WeatherStatus> {
  const payload = await apiPostEmpty<unknown>('/api/weather/refresh')
  const record = asRecord(payload)

  return {
    provider_status: normalizeWeatherProviderState(record?.provider_status),
    current_conditions: record?.current_conditions ? normalizeWeatherCurrentConditions(record.current_conditions) : null,
    dominant_alert: record?.dominant_alert ? normalizeWeatherAlert(record.dominant_alert) : null,
    active_alert_count: asNumber(record?.active_alert_count, 0),
    current_display_action: asString(record?.current_display_action, 'none'),
    recent_refresh_runs: asArray(record?.recent_refresh_runs, (item) => normalizeWeatherRefreshRun(item)),
  }
}

export async function getDisplayWeather(): Promise<DisplayWeather> {
  const payload = await apiGet<unknown>('/api/display/weather')
  const record = asRecord(payload)

  return {
    enabled: asBoolean(record?.enabled, false),
    position: normalizeWeatherPosition(record?.position),
    units: normalizeWeatherUnits(record?.units),
    show_precipitation: asBoolean(record?.show_precipitation, true),
    show_humidity: asBoolean(record?.show_humidity, true),
    show_wind: asBoolean(record?.show_wind, true),
    provider_status: normalizeWeatherProviderState(record?.provider_status),
    current_conditions: record?.current_conditions ? normalizeWeatherCurrentConditions(record.current_conditions) : null,
  }
}

export async function getDisplayAlerts(): Promise<DisplayAlerts> {
  const payload = await apiGet<unknown>('/api/display/alerts')
  const record = asRecord(payload)

  return {
    provider_status: normalizeWeatherProviderState(record?.provider_status),
    dominant_alert: record?.dominant_alert ? normalizeWeatherAlert(record.dominant_alert) : null,
    active_alerts: asArray(record?.active_alerts, (item) => normalizeWeatherAlert(item)),
    presentation: normalizeDisplayAlertPresentation(record?.presentation),
  }
}

function normalizeWeatherSettings(payload: unknown): WeatherSettings {
  const record = asRecord(payload)

  return {
    weather_enabled: asBoolean(record?.weather_enabled, false),
    weather_provider: asString(record?.weather_provider, 'nws'),
    weather_location: normalizeWeatherLocation(record?.weather_location),
    weather_units: normalizeWeatherUnits(record?.weather_units),
    weather_position: normalizeWeatherPosition(record?.weather_position),
    weather_refresh_minutes: asNumber(record?.weather_refresh_minutes, 15),
    weather_show_precipitation: asBoolean(record?.weather_show_precipitation, true),
    weather_show_humidity: asBoolean(record?.weather_show_humidity, true),
    weather_show_wind: asBoolean(record?.weather_show_wind, true),
    weather_alerts_enabled: asBoolean(record?.weather_alerts_enabled, true),
    weather_alert_fullscreen_enabled: asBoolean(record?.weather_alert_fullscreen_enabled, true),
    weather_alert_minimum_severity: normalizeWeatherSeverity(record?.weather_alert_minimum_severity),
    weather_alert_repeat_enabled: asBoolean(record?.weather_alert_repeat_enabled, true),
    weather_alert_repeat_interval_minutes: asNumber(record?.weather_alert_repeat_interval_minutes, 5),
    weather_alert_repeat_display_seconds: asNumber(record?.weather_alert_repeat_display_seconds, 20),
  }
}

function normalizeWeatherLocation(payload: unknown): WeatherLocation {
  const record = asRecord(payload)
  return {
    label: asString(record?.label, ''),
    latitude: asOptionalNumber(record?.latitude) ?? null,
    longitude: asOptionalNumber(record?.longitude) ?? null,
  }
}

function normalizeWeatherProviderState(payload: unknown): WeatherProviderState {
  const record = asRecord(payload)
  return {
    provider_name: asString(record?.provider_name, 'nws'),
    provider_display_name: asString(record?.provider_display_name, 'National Weather Service'),
    status: asString(record?.status, 'disabled'),
    available: asBoolean(record?.available, false),
    configured: asBoolean(record?.configured, false),
    location_label: asString(record?.location_label, ''),
    last_weather_refresh_at: asOptionalString(record?.last_weather_refresh_at) ?? null,
    last_alert_refresh_at: asOptionalString(record?.last_alert_refresh_at) ?? null,
    last_successful_weather_refresh_at: asOptionalString(record?.last_successful_weather_refresh_at) ?? null,
    last_successful_alert_refresh_at: asOptionalString(record?.last_successful_alert_refresh_at) ?? null,
    current_error: asOptionalString(record?.current_error) ?? null,
    updated_at: asString(record?.updated_at, ''),
  }
}

function normalizeWeatherCurrentConditions(payload: unknown): WeatherCurrentConditions {
  const record = asRecord(payload)
  return {
    provider_name: asString(record?.provider_name, 'nws'),
    provider_display_name: asString(record?.provider_display_name, 'National Weather Service'),
    location_label: asString(record?.location_label, ''),
    condition: asString(record?.condition, 'Unavailable'),
    icon_token: asString(record?.icon_token, 'cloudy'),
    temperature: asOptionalNumber(record?.temperature) ?? null,
    temperature_unit: asString(record?.temperature_unit, 'F'),
    humidity_percent: asOptionalNumber(record?.humidity_percent) ?? null,
    wind_speed: asOptionalNumber(record?.wind_speed) ?? null,
    wind_unit: asString(record?.wind_unit, 'mph'),
    wind_direction: asOptionalString(record?.wind_direction) ?? null,
    precipitation_probability_percent: asOptionalNumber(record?.precipitation_probability_percent) ?? null,
    observed_at: asOptionalString(record?.observed_at) ?? null,
    fetched_at: asString(record?.fetched_at, ''),
    attribution: asString(record?.attribution, 'National Weather Service'),
    is_stale: asBoolean(record?.is_stale, false),
  }
}

function normalizeWeatherAlert(payload: unknown): WeatherAlert {
  const record = asRecord(payload)
  return {
    id: asString(record?.id, ''),
    provider_name: asString(record?.provider_name, 'nws'),
    provider_display_name: asString(record?.provider_display_name, 'National Weather Service'),
    event: asString(record?.event, 'Weather Alert'),
    severity: asString(record?.severity, 'unknown'),
    certainty: asString(record?.certainty, 'Unknown'),
    urgency: asString(record?.urgency, 'Unknown'),
    headline: asString(record?.headline, 'Weather Alert'),
    description: asString(record?.description, ''),
    instruction: asString(record?.instruction, ''),
    area: asString(record?.area, ''),
    status: asString(record?.status, 'Actual'),
    issued_at: asOptionalString(record?.issued_at) ?? null,
    effective_at: asOptionalString(record?.effective_at) ?? null,
    expires_at: asOptionalString(record?.expires_at) ?? null,
    ends_at: asOptionalString(record?.ends_at) ?? null,
    attribution: asString(record?.attribution, 'National Weather Service'),
    escalation_mode: asString(record?.escalation_mode, 'badge'),
    effective_escalation_mode: asString(record?.effective_escalation_mode, asString(record?.escalation_mode, 'badge')),
    display_priority: asNumber(record?.display_priority, 0),
    effective_display_priority: asNumber(record?.effective_display_priority, 0),
    event_priority: asNumber(record?.event_priority, 0),
    is_active: asBoolean(record?.is_active, true),
    is_dominant: asBoolean(record?.is_dominant, false),
  }
}

function normalizeWeatherRefreshRun(payload: unknown): WeatherRefreshRun {
  const record = asRecord(payload)
  return {
    id: asString(record?.id, ''),
    provider_name: asString(record?.provider_name, 'nws'),
    refresh_kind: asString(record?.refresh_kind, 'weather'),
    trigger: asString(record?.trigger, 'manual'),
    status: asString(record?.status, 'unknown'),
    message: asString(record?.message, ''),
    error_message: asOptionalString(record?.error_message) ?? null,
    started_at: asString(record?.started_at, ''),
    completed_at: asOptionalString(record?.completed_at) ?? null,
  }
}

function normalizeDisplayAlertPresentation(payload: unknown): DisplayAlertPresentation {
  const record = asRecord(payload)
  return {
    mode: asString(record?.mode, 'none'),
    fallback_mode: asOptionalString(record?.fallback_mode) ?? null,
    repeat_interval_minutes: asNumber(record?.repeat_interval_minutes, 5),
    repeat_display_seconds: asNumber(record?.repeat_display_seconds, 20),
    alert_count: asNumber(record?.alert_count, 0),
  }
}

function normalizeWeatherPosition(value: unknown): DisplayWeather['position'] {
  switch (value) {
    case 'top-left':
    case 'top-right':
    case 'bottom-left':
    case 'bottom-right':
      return value
    default:
      return 'top-right'
  }
}

function normalizeWeatherUnits(value: unknown): DisplayWeather['units'] {
  return value === 'c' ? 'c' : 'f'
}

function normalizeWeatherSeverity(value: unknown): WeatherSettings['weather_alert_minimum_severity'] {
  switch (value) {
    case 'unknown':
    case 'minor':
    case 'moderate':
    case 'severe':
    case 'extreme':
      return value
    default:
      return 'minor'
  }
}
