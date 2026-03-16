import type { DisplayWeather } from '../api/types'

interface WeatherWidgetProps {
  weather: DisplayWeather
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

  return (
    <section className={`display-weather-widget display-weather-widget--${weather.position}`} aria-label="Current weather">
      <div className="display-weather-widget__icon" aria-hidden="true">
        {ICONS[current.icon_token] ?? '☁'}
      </div>
      <div className="display-weather-widget__summary">
        <div className="display-weather-widget__temperature">
          {current.temperature ?? '—'}°{current.temperature_unit}
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
