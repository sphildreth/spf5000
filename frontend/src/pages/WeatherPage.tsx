import { useEffect, useState } from 'react'

import { getWeatherAlerts, getWeatherSettings, getWeatherStatus, refreshWeather, updateWeatherSettings } from '../api/weather'
import type { WeatherSettings, WeatherStatus, WeatherAlertsState } from '../api/types'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { StatusNotice } from '../components/StatusNotice'
import { useAsyncData } from '../hooks/useAsyncData'
import { formatDateTime, toTitleCase } from '../utils/format'

interface WeatherPageData {
  settings: WeatherSettings
  status: WeatherStatus
  alerts: WeatherAlertsState
}

export function WeatherPage() {
  const { data, loading, error, reload, setData } = useAsyncData<WeatherPageData>(
    async () => {
      const [settings, status, alerts] = await Promise.all([getWeatherSettings(), getWeatherStatus(), getWeatherAlerts()])
      return { settings, status, alerts }
    },
    [],
  )
  const [draft, setDraft] = useState<WeatherSettings | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshError, setRefreshError] = useState<string | null>(null)
  const [refreshSuccess, setRefreshSuccess] = useState(false)

  useEffect(() => {
    if (data) {
      setDraft(data.settings)
    }
  }, [data])

  async function handleSave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!draft) {
      return
    }

    try {
      setSaveError(null)
      setSaved(false)
      const updated = await updateWeatherSettings(draft)
      setData((current) => (current ? { ...current, settings: updated } : current))
      setDraft(updated)
      setSaved(true)
    } catch (caught) {
      setSaveError(caught instanceof Error ? caught.message : 'Could not save weather settings.')
    }
  }

  async function handleRefresh() {
    try {
      setRefreshing(true)
      setRefreshError(null)
      setRefreshSuccess(false)
      const [status, alerts] = await Promise.all([refreshWeather(), getWeatherAlerts()])
      setData((current) => (current ? { ...current, status, alerts } : current))
      setRefreshSuccess(true)
    } catch (caught) {
      setRefreshError(caught instanceof Error ? caught.message : 'Could not refresh weather data.')
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        title="Weather & alerts"
        description="Configure the display weather widget, keep cached weather data fresh, and review the alert escalation state driving the fullscreen display."
        actions={
          <div className="button-row">
            <button type="button" className="button button--ghost" onClick={() => void reload()}>
              Reload
            </button>
            <button type="button" className="button" disabled={refreshing} onClick={() => void handleRefresh()}>
              {refreshing ? 'Refreshing…' : 'Refresh now'}
            </button>
          </div>
        }
      />

      {loading ? <StatusNotice variant="loading" title="Loading weather settings…" /> : null}
      {error ? <StatusNotice variant="error" title="Could not load weather data" detail={error} /> : null}
      {saveError ? <StatusNotice variant="error" title="Could not save weather settings" detail={saveError} /> : null}
      {saved ? <StatusNotice variant="success" title="Weather settings saved" /> : null}
      {refreshError ? <StatusNotice variant="error" title="Could not refresh weather data" detail={refreshError} /> : null}
      {refreshSuccess ? <StatusNotice variant="success" title="Weather cache refreshed" /> : null}

      {draft && data ? (
        <>
          <div className="two-column-grid">
            <Card title="Widget settings" eyebrow="Display overlay">
              <form className="form-grid" onSubmit={(event) => void handleSave(event)}>
                <label className="checkbox-field">
                  <input
                    type="checkbox"
                    checked={draft.weather_enabled}
                    onChange={(event) => setDraft((current) => (current ? { ...current, weather_enabled: event.target.checked } : current))}
                  />
                  <span>Enable weather widget and provider refresh</span>
                </label>

                <label>
                  <span>Provider</span>
                  <select
                    value={draft.weather_provider}
                    onChange={(event) => setDraft((current) => (current ? { ...current, weather_provider: event.target.value } : current))}
                  >
                    <option value="nws">National Weather Service</option>
                  </select>
                </label>

                <label>
                  <span>Location label</span>
                  <input
                    type="text"
                    value={draft.weather_location.label}
                    onChange={(event) =>
                      setDraft((current) =>
                        current
                          ? {
                              ...current,
                              weather_location: { ...current.weather_location, label: event.target.value },
                            }
                          : current,
                      )
                    }
                  />
                </label>

                <label>
                  <span>Latitude</span>
                  <input
                    type="number"
                    step="0.0001"
                    value={draft.weather_location.latitude ?? ''}
                    onChange={(event) =>
                      setDraft((current) =>
                        current
                          ? {
                              ...current,
                              weather_location: {
                                ...current.weather_location,
                                latitude: event.target.value ? Number(event.target.value) : null,
                              },
                            }
                          : current,
                      )
                    }
                  />
                </label>

                <label>
                  <span>Longitude</span>
                  <input
                    type="number"
                    step="0.0001"
                    value={draft.weather_location.longitude ?? ''}
                    onChange={(event) =>
                      setDraft((current) =>
                        current
                          ? {
                              ...current,
                              weather_location: {
                                ...current.weather_location,
                                longitude: event.target.value ? Number(event.target.value) : null,
                              },
                            }
                          : current,
                      )
                    }
                  />
                </label>

                <label>
                  <span>Units</span>
                  <select
                    value={draft.weather_units}
                    onChange={(event) =>
                      setDraft((current) =>
                        current ? { ...current, weather_units: event.target.value as WeatherSettings['weather_units'] } : current,
                      )
                    }
                  >
                    <option value="f">Fahrenheit</option>
                    <option value="c">Celsius</option>
                  </select>
                </label>

                <label>
                  <span>Widget position</span>
                  <select
                    value={draft.weather_position}
                    onChange={(event) =>
                      setDraft((current) =>
                        current ? { ...current, weather_position: event.target.value as WeatherSettings['weather_position'] } : current,
                      )
                    }
                  >
                    <option value="top-left">Top left</option>
                    <option value="top-right">Top right</option>
                    <option value="bottom-left">Bottom left</option>
                    <option value="bottom-right">Bottom right</option>
                  </select>
                </label>

                <label>
                  <span>Weather refresh cadence (minutes)</span>
                  <input
                    type="number"
                    min={1}
                    max={180}
                    value={draft.weather_refresh_minutes}
                    onChange={(event) =>
                      setDraft((current) =>
                        current ? { ...current, weather_refresh_minutes: Number(event.target.value) } : current,
                      )
                    }
                  />
                </label>

                <label className="checkbox-field">
                  <input
                    type="checkbox"
                    checked={draft.weather_show_precipitation}
                    onChange={(event) =>
                      setDraft((current) => (current ? { ...current, weather_show_precipitation: event.target.checked } : current))
                    }
                  />
                  <span>Show precipitation chance</span>
                </label>

                <label className="checkbox-field">
                  <input
                    type="checkbox"
                    checked={draft.weather_show_humidity}
                    onChange={(event) =>
                      setDraft((current) => (current ? { ...current, weather_show_humidity: event.target.checked } : current))
                    }
                  />
                  <span>Show humidity</span>
                </label>

                <label className="checkbox-field">
                  <input
                    type="checkbox"
                    checked={draft.weather_show_wind}
                    onChange={(event) =>
                      setDraft((current) => (current ? { ...current, weather_show_wind: event.target.checked } : current))
                    }
                  />
                  <span>Show wind</span>
                </label>

                <div className="form-actions">
                  <button type="submit" className="button">
                    Save weather settings
                  </button>
                </div>
              </form>
            </Card>

            <Card title="Alert behavior" eyebrow="Display escalation">
              <form className="form-grid" onSubmit={(event) => void handleSave(event)}>
                <label className="checkbox-field">
                  <input
                    type="checkbox"
                    checked={draft.weather_alerts_enabled}
                    onChange={(event) =>
                      setDraft((current) => (current ? { ...current, weather_alerts_enabled: event.target.checked } : current))
                    }
                  />
                  <span>Enable weather alerts on the display</span>
                </label>

                <label className="checkbox-field">
                  <input
                    type="checkbox"
                    checked={draft.weather_alert_fullscreen_enabled}
                    onChange={(event) =>
                      setDraft((current) =>
                        current ? { ...current, weather_alert_fullscreen_enabled: event.target.checked } : current,
                      )
                    }
                  />
                  <span>Allow fullscreen alert takeover</span>
                </label>

                <label>
                  <span>Minimum alert severity</span>
                  <select
                    value={draft.weather_alert_minimum_severity}
                    onChange={(event) =>
                      setDraft((current) =>
                        current
                          ? {
                              ...current,
                              weather_alert_minimum_severity: event.target.value as WeatherSettings['weather_alert_minimum_severity'],
                            }
                          : current,
                      )
                    }
                  >
                    <option value="unknown">Unknown</option>
                    <option value="minor">Minor</option>
                    <option value="moderate">Moderate</option>
                    <option value="severe">Severe</option>
                    <option value="extreme">Extreme</option>
                  </select>
                </label>

                <label className="checkbox-field">
                  <input
                    type="checkbox"
                    checked={draft.weather_alert_repeat_enabled}
                    onChange={(event) =>
                      setDraft((current) => (current ? { ...current, weather_alert_repeat_enabled: event.target.checked } : current))
                    }
                  />
                  <span>Repeat critical fullscreen alerts</span>
                </label>

                <label>
                  <span>Repeat interval (minutes)</span>
                  <input
                    type="number"
                    min={1}
                    max={120}
                    value={draft.weather_alert_repeat_interval_minutes}
                    onChange={(event) =>
                      setDraft((current) =>
                        current ? { ...current, weather_alert_repeat_interval_minutes: Number(event.target.value) } : current,
                      )
                    }
                  />
                </label>

                <label>
                  <span>Fullscreen display duration (seconds)</span>
                  <input
                    type="number"
                    min={5}
                    max={300}
                    value={draft.weather_alert_repeat_display_seconds}
                    onChange={(event) =>
                      setDraft((current) =>
                        current ? { ...current, weather_alert_repeat_display_seconds: Number(event.target.value) } : current,
                      )
                    }
                  />
                </label>

                <div className="form-actions">
                  <button type="submit" className="button">
                    Save alert settings
                  </button>
                </div>
              </form>
            </Card>
          </div>

          <div className="two-column-grid">
            <Card title="Provider status" eyebrow="Cache and health">
              <dl className="detail-list">
                <div>
                  <dt>Provider</dt>
                  <dd>{data.status.provider_status.provider_display_name}</dd>
                </div>
                <div>
                  <dt>Status</dt>
                  <dd>
                    <span className={`pill pill--${data.status.provider_status.status === 'ready' ? 'ok' : 'warning'}`}>
                      {toTitleCase(data.status.provider_status.status)}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt>Configured location</dt>
                  <dd>{data.status.provider_status.location_label || 'Not configured'}</dd>
                </div>
                <div>
                  <dt>Last weather refresh</dt>
                  <dd>{formatDateTime(data.status.provider_status.last_weather_refresh_at)}</dd>
                </div>
                <div>
                  <dt>Last alert refresh</dt>
                  <dd>{formatDateTime(data.status.provider_status.last_alert_refresh_at)}</dd>
                </div>
                <div>
                  <dt>Display action</dt>
                  <dd>{toTitleCase(data.status.current_display_action.replace(/_/g, ' '))}</dd>
                </div>
              </dl>
              {data.status.provider_status.current_error ? (
                <StatusNotice variant="error" title="Weather provider error" detail={data.status.provider_status.current_error} />
              ) : (
                <p className="card-muted">The display reads cached weather state from the backend and never waits on live NWS requests.</p>
              )}
            </Card>

            <Card title="Current conditions" eyebrow="Cached weather">
              {data.status.current_conditions ? (
                <dl className="detail-list">
                  <div>
                    <dt>Condition</dt>
                    <dd>{data.status.current_conditions.condition}</dd>
                  </div>
                  <div>
                    <dt>Temperature</dt>
                    <dd>
                      {data.status.current_conditions.temperature ?? '—'}°{data.status.current_conditions.temperature_unit}
                    </dd>
                  </div>
                  <div>
                    <dt>Humidity</dt>
                    <dd>{data.status.current_conditions.humidity_percent ?? '—'}%</dd>
                  </div>
                  <div>
                    <dt>Wind</dt>
                    <dd>
                      {data.status.current_conditions.wind_speed ?? '—'} {data.status.current_conditions.wind_unit}
                      {data.status.current_conditions.wind_direction ? ` ${data.status.current_conditions.wind_direction}` : ''}
                    </dd>
                  </div>
                  <div>
                    <dt>Precipitation</dt>
                    <dd>{data.status.current_conditions.precipitation_probability_percent ?? '—'}%</dd>
                  </div>
                  <div>
                    <dt>Observed</dt>
                    <dd>{formatDateTime(data.status.current_conditions.observed_at)}</dd>
                  </div>
                </dl>
              ) : (
                <StatusNotice
                  variant="empty"
                  title="No cached conditions yet"
                  detail="Set a location, enable weather, and run a refresh to populate the cache."
                />
              )}
            </Card>
          </div>

          <div className="two-column-grid">
            <Card title="Active alerts" eyebrow="Escalation visibility">
              {data.alerts.active_alerts.length > 0 ? (
                <ul className="simple-list">
                  {data.alerts.active_alerts.map((alert) => (
                    <li key={alert.id}>
                      <div>
                        <strong>{alert.event}</strong>
                        <p>
                          {alert.area} · {toTitleCase(alert.severity)} · {toTitleCase(alert.effective_escalation_mode.replace(/_/g, ' '))}
                        </p>
                      </div>
                      <span className={`pill pill--${alert.is_dominant ? 'warning' : 'muted'}`}>
                        {alert.is_dominant ? 'Dominant' : 'Active'}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <StatusNotice variant="empty" title="No active alerts" detail="Cached alerts will appear here after the next alert refresh." />
              )}
            </Card>

            <Card title="Recent refresh activity" eyebrow="Background sync">
              {data.status.recent_refresh_runs.length > 0 ? (
                <ul className="simple-list">
                  {data.status.recent_refresh_runs.map((run) => (
                    <li key={run.id}>
                      <div>
                        <strong>{toTitleCase(run.refresh_kind)}</strong>
                        <p>
                          {toTitleCase(run.status)} · {run.trigger} · {formatDateTime(run.completed_at ?? run.started_at)}
                        </p>
                      </div>
                      <span className={`pill pill--${run.status === 'completed' ? 'ok' : run.status === 'failed' ? 'warning' : 'muted'}`}>
                        {toTitleCase(run.status)}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="card-muted">No weather refresh runs have been recorded yet.</p>
              )}
            </Card>
          </div>
        </>
      ) : null}
    </div>
  )
}
