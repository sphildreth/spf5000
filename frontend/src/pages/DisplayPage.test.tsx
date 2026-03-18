import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, waitFor, cleanup } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { getDefaultDisplayConfig, getDisplayPlaylist } from '../api/display'
import { getDisplayAlerts, getDisplayWeather } from '../api/weather'
import type { DisplayAlerts, DisplayPlaylist, DisplayWeather } from '../api/types'
import { DisplayPage } from './DisplayPage'

vi.mock('../api/display', async () => {
  const actual = await vi.importActual<typeof import('../api/display')>('../api/display')
  return {
    ...actual,
    getDisplayPlaylist: vi.fn(),
  }
})

vi.mock('../api/weather', async () => {
  const actual = await vi.importActual<typeof import('../api/weather')>('../api/weather')
  return {
    ...actual,
    getDisplayWeather: vi.fn(),
    getDisplayAlerts: vi.fn(),
  }
})

vi.mock('../components/WeatherWidget', () => ({
  WeatherWidget: () => null,
}))

vi.mock('../components/WeatherAlertOverlay', () => ({
  WeatherAlertOverlay: () => null,
}))

function emptyPlaylist(overrides: Partial<DisplayPlaylist> = {}): DisplayPlaylist {
  return {
    collection_id: null,
    collection_name: null,
    shuffle_enabled: true,
    playlist_revision: 'empty',
    profile: getDefaultDisplayConfig(),
    items: [],
    sleep_schedule: null,
    ...overrides,
  }
}

function displayWeather(): DisplayWeather {
  return {
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
}

function displayAlerts(): DisplayAlerts {
  return {
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
}

function renderDisplayPage() {
  return render(
    <MemoryRouter initialEntries={['/display']}>
      <Routes>
        <Route path="/display" element={<DisplayPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('DisplayPage', () => {
  beforeEach(() => {
    vi.mocked(getDisplayPlaylist).mockResolvedValue(emptyPlaylist())
    vi.mocked(getDisplayWeather).mockResolvedValue(displayWeather())
    vi.mocked(getDisplayAlerts).mockResolvedValue(displayAlerts())

    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockReturnValue({
        matches: false,
        media: '',
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }),
    })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('shows a stable no-images message when the playlist is empty', async () => {
    renderDisplayPage()

    expect(await screen.findByRole('heading', { name: /no images found/i })).toBeInTheDocument()
    expect(screen.getByText(/add photos from the admin ui to begin playback/i)).toBeInTheDocument()

    await waitFor(() => {
      expect(getDisplayPlaylist).toHaveBeenCalledTimes(1)
    })
  })
})
