import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { WeatherWidget } from './WeatherWidget'
import type { DisplayWeather } from '../api/types'

const _weather = (overrides: Partial<DisplayWeather> = {}): DisplayWeather => ({
  enabled: true,
  position: 'top-right',
  current_conditions: {
    icon_token: 'sunny',
    temperature: 72,
    temperature_unit: 'F',
    condition: 'Sunny',
    location_label: 'Overland Park, KS',
    is_stale: false,
    humidity_percent: 55,
    precipitation_probability_percent: 10,
    wind_speed: '8',
    wind_unit: 'mph',
    wind_direction: 'S',
    observed_at: '2026-03-18T10:00:00Z',
    fetched_at: '2026-03-18T10:00:00Z',
  },
  ...overrides,
})

describe('WeatherWidget', () => {
  it('renders weather data correctly', () => {
    render(<WeatherWidget weather={_weather()} />)
    expect(screen.getByText('72°F')).toBeInTheDocument()
    expect(screen.getByText('Sunny')).toBeInTheDocument()
    expect(screen.getByText('Overland Park, KS')).toBeInTheDocument()
  })

  it('uses correct aria-label for weather icon', () => {
    render(<WeatherWidget weather={_weather({ current_conditions: { ..._weather().current_conditions, icon_token: 'rain' } })} />)
    const icon = screen.getByRole('img', { hidden: true })
    expect(icon).toHaveAttribute('aria-label', 'Rain')
  })

  it('shows fallback aria-label for unknown icon token', () => {
    render(<WeatherWidget weather={_weather({ current_conditions: { ..._weather().current_conditions, icon_token: 'tornado' as DisplayWeather['current_conditions']['icon_token'] } })} />)
    const icon = screen.getByRole('img', { hidden: true })
    expect(icon).toHaveAttribute('aria-label', 'Weather')
  })

  it('returns null when weather is disabled', () => {
    const { container } = render(<WeatherWidget weather={_weather({ enabled: false })} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('shows stale indicator when data is stale', () => {
    render(<WeatherWidget weather={_weather({ current_conditions: { ..._weather().current_conditions, is_stale: true } })} />)
    expect(screen.getByText('Cached weather')).toBeInTheDocument()
  })

  it('displays wind speed and direction', () => {
    render(<WeatherWidget weather={_weather({ show_wind: true })} />)
    expect(screen.getByText(/8 mph S/i)).toBeInTheDocument()
  })

  it('does not render wind section when show_wind is false', () => {
    render(<WeatherWidget weather={_weather({ show_wind: false })} />)
    expect(screen.queryByText(/mph/)).not.toBeInTheDocument()
  })

  it('displays precipitation when enabled', () => {
    render(<WeatherWidget weather={_weather({ show_precipitation: true })} />)
    expect(screen.getByText(/10%/)).toBeInTheDocument()
    expect(screen.getByText('Precip')).toBeInTheDocument()
  })

  it('displays humidity when enabled', () => {
    render(<WeatherWidget weather={_weather({ show_humidity: true })} />)
    expect(screen.getByText('Humidity')).toBeInTheDocument()
    expect(screen.getByText(/55%/)).toBeInTheDocument()
  })

  it('has aria-label on section', () => {
    render(<WeatherWidget weather={_weather()} />)
    expect(screen.getByRole('region', { hidden: true })).toBeInTheDocument()
  })
})
