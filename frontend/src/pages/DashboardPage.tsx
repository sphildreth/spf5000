import { useMemo } from 'react'

import { getAssets } from '../api/assets'
import { getCollections } from '../api/collections'
import { getDisplayConfig } from '../api/display'
import { getSettings } from '../api/settings'
import { getSources } from '../api/sources'
import { getStatus } from '../api/status'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { StatusNotice } from '../components/StatusNotice'
import { useAsyncData } from '../hooks/useAsyncData'
import { formatDateTime, formatNumber, toTitleCase } from '../utils/format'

interface DashboardData {
  status: Awaited<ReturnType<typeof getStatus>>
  settings: Awaited<ReturnType<typeof getSettings>>
  sources: Awaited<ReturnType<typeof getSources>>
  assets: Awaited<ReturnType<typeof getAssets>>
  collections: Awaited<ReturnType<typeof getCollections>>
  displayConfig: Awaited<ReturnType<typeof getDisplayConfig>>
}

export function DashboardPage() {
  const { data, loading, error, reload } = useAsyncData<DashboardData>(
    async () => {
      const [status, settings, sources, assets, collections, displayConfig] = await Promise.all([
        getStatus(),
        getSettings(),
        getSources(),
        getAssets(),
        getCollections(),
        getDisplayConfig(),
      ])

      return { status, settings, sources, assets, collections, displayConfig }
    },
    [],
  )

  const statCards = useMemo(() => {
    if (!data) {
      return []
    }

    return [
      {
        label: 'Assets',
        value: formatNumber(data.status.asset_count ?? data.assets.length),
        detail: 'Photos ready for playback',
      },
      {
        label: 'Collections',
        value: formatNumber(data.status.collection_count ?? data.collections.length),
        detail: 'Display groupings configured',
      },
      {
        label: 'Sources',
        value: formatNumber(data.status.source_count ?? data.sources.length),
        detail: 'Import and provider entries',
      },
      {
        label: 'Playback',
        value: data.displayConfig.playback_mode === 'shuffle' ? 'Shuffle' : 'Sequential',
        detail: `${data.displayConfig.interval_seconds}s dwell · ${data.displayConfig.fit_mode}`,
      },
    ]
  }, [data])

  return (
    <div className="page-stack">
      <PageHeader
        title="Dashboard"
        description="Status, counts, and the key playback settings that matter most day to day."
        actions={
          <button type="button" className="button button--ghost" onClick={() => void reload()}>
            Refresh
          </button>
        }
      />

      {loading ? <StatusNotice variant="loading" title="Loading dashboard…" /> : null}
      {error ? <StatusNotice variant="error" title="Could not load dashboard" detail={error} /> : null}

      {data ? (
        <>
          <div className="stats-grid">
            {statCards.map((card) => (
              <Card key={card.label} className="stat-card">
                <p className="eyebrow">{card.label}</p>
                <strong className="stat-card-value">{card.value}</strong>
                <p className="card-muted">{card.detail}</p>
              </Card>
            ))}
          </div>

          <div className="two-column-grid">
            <Card title="Frame status" eyebrow="System">
              <dl className="detail-list">
                <div>
                  <dt>Application</dt>
                  <dd>{data.status.app}</dd>
                </div>
                <div>
                  <dt>State</dt>
                  <dd>
                    <span className={`pill pill--${data.status.ok ? 'ok' : 'warning'}`}>
                      {toTitleCase(data.status.status)}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt>Hostname</dt>
                  <dd>{data.status.hostname ?? '—'}</dd>
                </div>
                <div>
                  <dt>Version</dt>
                  <dd>{data.status.version ?? '—'}</dd>
                </div>
                <div>
                  <dt>Last sync</dt>
                  <dd>{formatDateTime(data.status.last_sync_at)}</dd>
                </div>
              </dl>
              {data.status.warnings.length > 0 ? (
                <div className="inline-list">
                  {data.status.warnings.map((warning) => (
                    <span key={warning} className="pill pill--warning">
                      {warning}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="card-muted">No system warnings reported.</p>
              )}
            </Card>

            <Card title="Current playback defaults" eyebrow="Display">
              <dl className="detail-list">
                <div>
                  <dt>Dwell time</dt>
                  <dd>{data.settings.slideshow_interval_seconds} seconds</dd>
                </div>
                <div>
                  <dt>Transition</dt>
                  <dd>{toTitleCase(data.settings.transition_mode)}</dd>
                </div>
                <div>
                  <dt>Fit mode</dt>
                  <dd>{toTitleCase(data.displayConfig.fit_mode)}</dd>
                </div>
                <div>
                  <dt>Transition duration</dt>
                  <dd>{data.displayConfig.transition_duration_ms} ms</dd>
                </div>
              </dl>
              <p className="card-muted">
                The display route stays separate from the admin shell and uses a dual-layer slide renderer.
              </p>
            </Card>
          </div>

          <div className="two-column-grid">
            <Card title="Sources" eyebrow="Connected">
              {data.sources.length > 0 ? (
                <ul className="simple-list">
                  {data.sources.map((source) => (
                    <li key={source.id}>
                      <div>
                        <strong>{source.name}</strong>
                        <p>{source.path ?? source.kind}</p>
                      </div>
                      <span className={`pill pill--${source.enabled ? 'ok' : 'muted'}`}>{source.status}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <StatusNotice
                  variant="empty"
                  title="No sources configured"
                  detail="Add a local source to begin importing photos onto the frame."
                />
              )}
            </Card>

            <Card title="Collections" eyebrow="Ready to play">
              {data.collections.length > 0 ? (
                <ul className="simple-list">
                  {data.collections.slice(0, 5).map((collection) => (
                    <li key={collection.id}>
                      <div>
                        <strong>{collection.name}</strong>
                        <p>{collection.description ?? 'No description yet.'}</p>
                      </div>
                      <span className="pill pill--muted">{formatNumber(collection.asset_count)} assets</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <StatusNotice
                  variant="empty"
                  title="No collections yet"
                  detail="Create a collection to control what the display page can show."
                />
              )}
            </Card>
          </div>
        </>
      ) : null}
    </div>
  )
}
