import type { CSSProperties } from 'react'
import type { DisplayWeather } from '../api/types'

interface WeatherWidgetProps {
  weather: DisplayWeather
}

const ICON_LABELS: Record<string, string> = {
  sunny: 'Sunny',
  'partly-cloudy': 'Partly cloudy',
  cloudy: 'Cloudy',
  rain: 'Rain',
  thunderstorm: 'Thunderstorm',
  snow: 'Snow',
  fog: 'Foggy',
  wind: 'Windy',
  ice: 'Icy',
}

const ICONS: Record<string, string> = {
  sunny: '☀',
  'partly-cloudy': '⛅',
  cloudy: '☁',
  rain: '🌧',
  thunderstorm: '⛈',
  snow: '❄',
  fog: '🌫',
  wind: '🌀',
  ice: '🧊',
}

export function WeatherWidget({ weather }: WeatherWidgetProps) {
  const current = weather.current_conditions
  if (!weather.enabled || !current) {
    return null
  }

  const isVerticalLayout = weather.position === 'left' || weather.position === 'right'
  const scale = weather.scale >= 1 ? weather.scale : 1

  return (
    <section
      className={`display-weather-widget display-weather-widget--${weather.position}${isVerticalLayout ? ' display-weather-widget--vertical' : ''}`}
      aria-label="Current weather"
      style={{ '--weather-widget-scale': String(scale) } as CSSProperties}
    >
      {!isVerticalLayout && (
        <div className="display-weather-widget__icon" role="img" aria-label={ICON_LABELS[current.icon_token] ?? 'Weather'}>
          {ICONS[current.icon_token] ?? '☁'}
        </div>
      )}
      <div className="display-weather-widget__summary">
        <div className={`display-weather-widget__temperature${isVerticalLayout ? ' display-weather-widget__temperature--large' : ''}`}>
          {current.temperature ?? '—'}{!isVerticalLayout && <>°{current.temperature_unit}</>}
        </div>
        <div className="display-weather-widget__condition">{current.condition}</div>
        <div className="display-weather-widget__location">{current.location_label}</div>
      </div>
      <dl className="display-weather-widget__details">
        {weather.show_precipitation ? (
          <div>
            <dt>Precip</dt>
            <dd>{current.precipitation_probability_percent ?? '—'}%</dd>
          </div>
        ) : null}
        {weather.show_humidity ? (
          <div>
            <dt>Humidity</dt>
            <dd>{current.humidity_percent ?? '—'}%</dd>
          </div>
        ) : null}
        {weather.show_wind ? (
          <div>
            <dt>Wind</dt>
            <dd>
              {current.wind_speed ?? '—'} {current.wind_unit}
              {current.wind_direction ? ` ${current.wind_direction}` : ''}
            </dd>
          </div>
        ) : null}
      </dl>
      {current.is_stale ? <div className="display-weather-widget__stale">Cached weather</div> : null}
    </section>
  )
}
