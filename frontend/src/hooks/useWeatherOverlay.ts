import { useCallback, useRef, useState } from 'react'
import { getDisplayAlerts, getDisplayWeather } from '../api/weather'
import type { DisplayAlerts, DisplayWeather } from '../api/types'

const EMPTY_DISPLAY_WEATHER: DisplayWeather = {
  enabled: false,
  position: 'top-right',
  units: 'f',
  show_precipitation: true,
  show_humidity: true,
  show_wind: true,
  provider_status: {
    provider_name: 'nws',
    provider_display_name: 'National Weather Service',
    status: 'disabled',
    available: true,
    configured: false,
    location_label: '',
    last_weather_refresh_at: null,
    last_alert_refresh_at: null,
    last_successful_weather_refresh_at: null,
    last_successful_alert_refresh_at: null,
    current_error: null,
    updated_at: '',
  },
  current_conditions: null,
}

const EMPTY_DISPLAY_ALERTS: DisplayAlerts = {
  provider_status: {
    provider_name: 'nws',
    provider_display_name: 'National Weather Service',
    status: 'disabled',
    available: true,
    configured: false,
    location_label: '',
    last_weather_refresh_at: null,
    last_alert_refresh_at: null,
    last_successful_weather_refresh_at: null,
    last_successful_alert_refresh_at: null,
    current_error: null,
    updated_at: '',
  },
  dominant_alert: null,
  active_alerts: [],
  presentation: {
    mode: 'none',
    fallback_mode: null,
    repeat_interval_minutes: 5,
    repeat_display_seconds: 20,
    alert_count: 0,
  },
}

export function useWeatherOverlay() {
  const [weather, setWeather] = useState<DisplayWeather>(EMPTY_DISPLAY_WEATHER)
  const [alerts, setAlerts] = useState<DisplayAlerts>(EMPTY_DISPLAY_ALERTS)

  const syncDisplayOverlays = useCallback(async () => {
    const [weatherResult, alertsResult] = await Promise.allSettled([getDisplayWeather(), getDisplayAlerts()])

    if (weatherResult.status === 'fulfilled') {
      setWeather(weatherResult.value)
    }

    if (alertsResult.status === 'fulfilled') {
      setAlerts(alertsResult.value)
    }
  }, [])

  return {
    weather,
    alerts,
    setWeather,
    setAlerts,
    syncDisplayOverlays,
    EMPTY_DISPLAY_WEATHER,
    EMPTY_DISPLAY_ALERTS,
  }
}

export function evaluateAlertFullscreenState(params: {
  isSleeping: boolean
  alerts: DisplayAlerts
  isFullscreenAlertActive: boolean
  activeRepeatAlertId: string | null
  nextFullscreenRepeatAt: number | null
}): {
  shouldBeActive: boolean
  nextRepeatAlertId: string | null
  nextRepeatAt: number | null
} {
  const { isSleeping, alerts, isFullscreenAlertActive, activeRepeatAlertId, nextFullscreenRepeatAt } = params
  const dominant = alerts.dominant_alert
  const mode = alerts.presentation.mode

  if (isSleeping) {
    return { shouldBeActive: false, nextRepeatAlertId: null, nextRepeatAt: null }
  }

  if (!dominant || (mode !== 'fullscreen' && mode !== 'fullscreen_repeat')) {
    return { shouldBeActive: false, nextRepeatAlertId: null, nextRepeatAt: null }
  }

  if (mode === 'fullscreen') {
    return { shouldBeActive: true, nextRepeatAlertId: dominant.id, nextRepeatAt: null }
  }

  if (isFullscreenAlertActive) {
    return { shouldBeActive: isFullscreenAlertActive, nextRepeatAlertId: activeRepeatAlertId, nextRepeatAt: nextFullscreenRepeatAt }
  }

  const now = Date.now()
  const newNextRepeatAt = nextFullscreenRepeatAt && now < nextFullscreenRepeatAt
    ? nextFullscreenRepeatAt
    : now + alerts.presentation.repeat_interval_minutes * 60 * 1000

  return { shouldBeActive: true, nextRepeatAlertId: dominant.id, nextRepeatAt: newNextRepeatAt }
}
