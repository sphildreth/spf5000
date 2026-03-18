import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { WeatherWidget } from './WeatherWidget'
import type { DisplayWeather } from '../api/types'

const FULL_CONDITIONS = {
  provider_name: 'nws',
  provider_display_name: 'National Weather Service',
  location_label: 'Overland Park, KS',
  condition: 'Sunny',
  icon_token: 'sunny',
  temperature: 72,
  temperature_unit: 'F',
  humidity_percent: 55,
  wind_speed: 8,
  wind_unit: 'mph',
  wind_direction: 'S',
  precipitation_probability_percent: 10,
  observed_at: '2026-03-18T10:00:00Z',
  fetched_at: '2026-03-18T10:00:00Z',
  attribution: 'National Weather Service',
  is_stale: false,
}

function weather(overrides: Partial<DisplayWeather> = {}): DisplayWeather {
  return {
    enabled: true,
    position: 'top-right',
    units: 'f',
    show_precipitation: false,
    show_humidity: false,
    show_wind: false,
    provider_status: {
      provider_name: 'nws',
      provider_display_name: 'National Weather Service',
      status: 'ready',
      available: true,
      configured: true,
      location_label: 'Overland Park, KS',
      last_weather_refresh_at: null,
      last_alert_refresh_at: null,
      last_successful_weather_refresh_at: null,
      last_successful_alert_refresh_at: null,
      current_error: null,
      updated_at: '',
    },
    current_conditions: { ...FULL_CONDITIONS },
    ...overrides,
  }
}

describe('WeatherWidget', () => {
  it('renders weather data correctly', () => {
    render(<WeatherWidget weather={weather()} />)
    expect(screen.getByText('72°F')).toBeInTheDocument()
    expect(screen.getByText('Sunny')).toBeInTheDocument()
    expect(screen.getByText('Overland Park, KS')).toBeInTheDocument()
  })

  it('uses correct aria-label for weather icon', () => {
    render(<WeatherWidget weather={weather({ current_conditions: { ...FULL_CONDITIONS, icon_token: 'rain' } })} />)
    const icon = screen.getByRole('img', { hidden: true })
    expect(icon).toHaveAttribute('aria-label', 'Rain')
  })

  it('shows fallback aria-label for unknown icon token', () => {
    render(<WeatherWidget weather={weather({ current_conditions: { ...FULL_CONDITIONS, icon_token: 'tornado' } })} />)
    const icon = screen.getByRole('img', { hidden: true })
    expect(icon).toHaveAttribute('aria-label', 'Weather')
  })

  it('returns null when weather is disabled', () => {
    const { container } = render(<WeatherWidget weather={weather({ enabled: false })} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('returns null when current_conditions is null', () => {
    const { container } = render(<WeatherWidget weather={weather({ current_conditions: null })} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('shows stale indicator when data is stale', () => {
    render(<WeatherWidget weather={weather({ current_conditions: { ...FULL_CONDITIONS, is_stale: true } })} />)
    expect(screen.getByText('Cached weather')).toBeInTheDocument()
  })

  it('displays wind speed and direction', () => {
    render(<WeatherWidget weather={weather({ show_wind: true })} />)
    expect(screen.getByText(/8 mph S/i)).toBeInTheDocument()
  })

  it('does not render wind section when show_wind is false', () => {
    render(<WeatherWidget weather={weather({ show_wind: false })} />)
    expect(screen.queryByText(/mph/)).not.toBeInTheDocument()
  })

  it('displays precipitation when enabled', () => {
    render(<WeatherWidget weather={weather({ show_precipitation: true })} />)
    expect(screen.getByText(/10%/)).toBeInTheDocument()
    expect(screen.getByText('Precip')).toBeInTheDocument()
  })

  it('displays humidity when enabled', () => {
    render(<WeatherWidget weather={weather({ show_humidity: true })} />)
    expect(screen.getByText('Humidity')).toBeInTheDocument()
    expect(screen.getByText(/55%/)).toBeInTheDocument()
  })

  it('has region role for weather section', () => {
    render(<WeatherWidget weather={weather()} />)
    expect(screen.getByRole('region', { hidden: true })).toBeInTheDocument()
  })
})
