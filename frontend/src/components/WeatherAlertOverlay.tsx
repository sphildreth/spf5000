import type { DisplayAlerts } from '../api/types'

interface WeatherAlertOverlayProps {
  alerts: DisplayAlerts
  fullscreenActive: boolean
}

export function WeatherAlertOverlay({ alerts, fullscreenActive }: WeatherAlertOverlayProps) {
  const dominant = alerts.dominant_alert
  if (!dominant) {
    return null
  }

  const mode = alerts.presentation.mode
  const fallbackMode = alerts.presentation.fallback_mode

  if (fullscreenActive && (mode === 'fullscreen' || mode === 'fullscreen_repeat')) {
    return (
      <section className="display-alert-fullscreen" role="alert" aria-live="assertive">
        <div className="display-alert-fullscreen__header">Weather Alert</div>
        <div className="display-alert-fullscreen__band">{dominant.event}</div>
        <div className="display-alert-fullscreen__body">
          <p className="display-alert-fullscreen__headline">{dominant.headline}</p>
          <p className="display-alert-fullscreen__area">{dominant.area}</p>
          <p className="display-alert-fullscreen__instruction">
            {summarizeText(dominant.instruction || dominant.description || dominant.headline)}
          </p>
          <dl className="display-alert-fullscreen__meta">
            <div>
              <dt>Severity</dt>
              <dd>{dominant.severity}</dd>
            </div>
            <div>
              <dt>Issued</dt>
              <dd>{formatTimestamp(dominant.issued_at)}</dd>
            </div>
            <div>
              <dt>Expires</dt>
              <dd>{formatTimestamp(dominant.expires_at)}</dd>
            </div>
            <div>
              <dt>Source</dt>
              <dd>{dominant.attribution}</dd>
            </div>
          </dl>
        </div>
      </section>
    )
  }

  if (mode === 'badge') {
    return (
      <aside className="display-alert-badge" role="status" aria-live="polite">
        <strong>Alert</strong>
        <span>{dominant.event}</span>
        {alerts.presentation.alert_count > 1 ? <em>{alerts.presentation.alert_count}</em> : null}
      </aside>
    )
  }

  if (mode === 'banner' || (mode === 'fullscreen_repeat' && fallbackMode === 'banner')) {
    return (
      <aside className="display-alert-banner" role="status" aria-live="polite">
        <div>
          <strong>{dominant.event}</strong>
          <p>{summarizeText(dominant.instruction || dominant.headline)}</p>
        </div>
        <span>{dominant.area}</span>
      </aside>
    )
  }

  return null
}

function summarizeText(value: string): string {
  const trimmed = value.trim()
  if (!trimmed) {
    return 'See the admin console for the latest alert details.'
  }
  const sentence = trimmed.split(/[.!?]\s/)[0] ?? trimmed
  return sentence.length > 180 ? `${sentence.slice(0, 177)}…` : sentence
}

function formatTimestamp(value: string | null): string {
  if (!value) {
    return '—'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
    month: 'short',
    day: 'numeric',
  }).format(date)
}
