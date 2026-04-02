import { useState } from 'react'

import { getAutoScanStatus, configureAutoScan, type AutoScanStatus } from '../api/autoScan'
import { runLocalImport, scanLocalSource } from '../api/import'
import { getSources } from '../api/sources'
import type {
  LocalImportScanResult,
  SourceSummary,
} from '../api/types'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { StatusNotice } from '../components/StatusNotice'
import { useAsyncData } from '../hooks/useAsyncData'
import { formatDateTime, formatNumber } from '../utils/format'

interface SourcesData {
  sources: Awaited<ReturnType<typeof getSources>>
  autoScan: AutoScanStatus
}

type BusyAction = 'scan' | 'run' | null

export function SourcesPage() {
  const { data, loading, error, reload, setData } = useAsyncData<SourcesData>(
    async () => {
      const [sources, autoScan] = await Promise.all([
        getSources(),
        getAutoScanStatus(),
      ])
      return { sources, autoScan }
    },
    [],
  )

  const [busyAction, setBusyAction] = useState<BusyAction>(null)
  const [scanResult, setScanResult] = useState<LocalImportScanResult | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [autoScanBusy, setAutoScanBusy] = useState(false)

  async function handleScanSource(source: SourceSummary) {
    setBusyAction('scan')
    setActionError(null)

    try {
      const result = await scanLocalSource({ source_id: source.id, max_samples: 10 })
      setScanResult(result)
      setFeedback(`Preview scan found ${formatNumber(result.discovered_count)} supported files.`)
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : 'Could not scan source.')
    } finally {
      setBusyAction(null)
    }
  }

  async function handleRunImport(source: SourceSummary) {
    setBusyAction('run')
    setActionError(null)

    try {
      await runLocalImport({
        source_id: source.id,
        collection_id: 'default-collection',
        max_samples: 10,
      })
      setFeedback(`Import started for "${source.name}". Files will be copied into the managed library.`)
      setScanResult(null)
      void reload()
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : 'Could not start import.')
    } finally {
      setBusyAction(null)
    }
  }

  const localSources = data?.sources ?? []

  return (
    <div className="page-stack">
      <PageHeader
        title="Sources & providers"
        description="Manage the local-files workflow and keep the frame stocked with cached photos for playback."
        actions={
          <button type="button" className="button button--ghost" onClick={() => void reload()}>
            Refresh
          </button>
        }
      />

      {feedback ? <StatusNotice variant="success" title={feedback} /> : null}
      {actionError ? <StatusNotice variant="error" title="Action failed" detail={actionError} /> : null}
      {loading ? <StatusNotice variant="loading" title="Loading sources…" /> : null}
      {error ? <StatusNotice variant="error" title="Could not load source data" detail={error} /> : null}

      {!loading && !error && localSources.length === 0 ? (
        <StatusNotice
          variant="empty"
          title="No local source configured"
          detail="The backend should bootstrap a default local-files source automatically."
        />
      ) : null}

      {!loading && !error ? (
        <Card
          title="Local Files"
          eyebrow={localSources[0]?.provider_type ?? 'local_files'}
        >
          <dl className="detail-list">
            <div>
              <dt>Name</dt>
              <dd>{localSources[0]?.name ?? '—'}</dd>
            </div>
            <div>
              <dt>Import path</dt>
              <dd>{localSources[0]?.import_path ?? '—'}</dd>
            </div>
            <div>
              <dt>Enabled</dt>
              <dd>{localSources[0]?.enabled ? 'Yes' : 'No'}</dd>
            </div>
            <div>
              <dt>Last scan</dt>
              <dd>{formatDateTime(localSources[0]?.last_scan_at) ?? '—'}</dd>
            </div>
            <div>
              <dt>Last import</dt>
              <dd>{formatDateTime(localSources[0]?.last_import_at) ?? '—'}</dd>
            </div>
            <div>
              <dt>Asset count</dt>
              <dd>{formatNumber(localSources[0]?.asset_count ?? 0)}</dd>
            </div>
          </dl>

          <p className="card-muted sources-helper-copy">
            Preview scan checks the import folder and shows what SPF5000 could ingest without changing the library.
            Import copies supported files into managed storage, generates variants, and adds them to the default collection.
          </p>

          <div className="form-actions">
            <button
              type="button"
              className="button"
              disabled={busyAction === 'scan'}
              onClick={() => localSources[0] && void handleScanSource(localSources[0])}
            >
              {busyAction === 'scan' ? 'Scanning…' : 'Preview scan'}
            </button>
            <button
              type="button"
              className="button button--ghost"
              disabled={busyAction === 'run'}
              onClick={() => localSources[0] && void handleRunImport(localSources[0])}
            >
              {busyAction === 'run' ? 'Importing…' : 'Import photos'}
            </button>
          </div>

          {scanResult ? (
            <Card title="Preview results" eyebrow="Dry run">
              <dl className="detail-list">
                <div>
                  <dt>Discovered</dt>
                  <dd>{formatNumber(scanResult.discovered_count)}</dd>
                </div>
                <div>
                  <dt>Ignored</dt>
                  <dd>{formatNumber(scanResult.ignored_count)}</dd>
                </div>
              </dl>
              {scanResult.sample_filenames.length > 0 ? (
                <div className="sources-sample-list">
                  <strong>Sample files:</strong>
                  <ul>
                    {scanResult.sample_filenames.slice(0, 5).map((name) => (
                      <li key={name}>{name}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </Card>
          ) : null}
        </Card>
      ) : (
        <StatusNotice
          variant="empty"
          title="No local source available"
          detail="Add or restore the local-files source before running an import."
        />
      )}

      {/* Auto-Scan Configuration Card */}
      <Card title="Automatic Scanning" eyebrow="Import automation">
        <p className="card-muted">
          Configure automatic scanning and importing of new photos. Photos can be scanned on a schedule
          or automatically when files are added to the import folder.
        </p>

        <div className="sources-automation-grid">
          <section className="sources-automation-section">
            <label className="checkbox-field settings-toggle-card">
              <input
                type="checkbox"
                checked={data?.autoScan.auto_scan_enabled ?? false}
                onChange={async (e) => {
                  setAutoScanBusy(true)
                  try {
                    const updated = await configureAutoScan({ auto_scan_enabled: e.target.checked })
                    setData((current) => current ? { ...current, autoScan: updated } : current)
                    setFeedback(e.target.checked ? 'Scheduled scanning enabled' : 'Scheduled scanning disabled')
                  } catch (err) {
                    setActionError(err instanceof Error ? err.message : 'Failed to update settings')
                  } finally {
                    setAutoScanBusy(false)
                  }
                }}
                disabled={autoScanBusy}
              />
              <span className="settings-toggle-card__copy">
                <span>Enable scheduled scanning</span>
                <span className="settings-toggle-card__note">
                  Automatically scan and import new photos on a schedule.
                </span>
              </span>
            </label>

            {data?.autoScan.auto_scan_enabled ? (
              <div className="sources-automation-config">
                <label>
                  <span>Cron schedule</span>
                  <input
                    type="text"
                    value={data.autoScan.auto_scan_cron_schedule}
                    placeholder="0 */4 * * *"
                    onChange={async (e) => {
                      setAutoScanBusy(true)
                      try {
                        const updated = await configureAutoScan({ auto_scan_cron_schedule: e.target.value })
                        setData((current) => current ? { ...current, autoScan: updated } : current)
                        setFeedback('Schedule updated')
                      } catch (err) {
                        setActionError(err instanceof Error ? err.message : 'Invalid cron expression')
                      } finally {
                        setAutoScanBusy(false)
                      }
                    }}
                    disabled={autoScanBusy}
                  />
                </label>
                <p className="sources-automation-hint">
                  Examples: <code>0 */4 * * *</code> every 4 hours, <code>0 3 * * *</code> daily at 3 AM, <code>0 * * * *</code> every hour.
                </p>
              </div>
            ) : null}
          </section>

          <section className="sources-automation-section">
            <label className="checkbox-field settings-toggle-card">
              <input
                type="checkbox"
                checked={data?.autoScan.auto_watch_enabled ?? false}
                onChange={async (e) => {
                  setAutoScanBusy(true)
                  try {
                    const updated = await configureAutoScan({ auto_watch_enabled: e.target.checked })
                    setData((current) => current ? { ...current, autoScan: updated } : current)
                    setFeedback(e.target.checked ? 'Auto-watch enabled' : 'Auto-watch disabled')
                  } catch (err) {
                    setActionError(err instanceof Error ? err.message : 'Failed to update settings')
                  } finally {
                    setAutoScanBusy(false)
                  }
                }}
                disabled={autoScanBusy}
              />
              <span className="settings-toggle-card__copy">
                <span>Enable auto-watch</span>
                <span className="settings-toggle-card__note">
                  Automatically scan and import when new files are detected in the import folder.
                </span>
              </span>
            </label>

            {data?.autoScan.auto_watch_enabled ? (
              <div className="sources-automation-config">
                <label>
                  <span>Debounce delay (seconds)</span>
                  <input
                    className="sources-automation-number"
                    type="number"
                    min="1"
                    max="60"
                    value={data.autoScan.auto_watch_debounce_seconds}
                    onChange={async (e) => {
                      setAutoScanBusy(true)
                      try {
                        const updated = await configureAutoScan({ auto_watch_debounce_seconds: parseInt(e.target.value, 10) })
                        setData((current) => current ? { ...current, autoScan: updated } : current)
                        setFeedback('Debounce delay updated')
                      } catch (err) {
                        setActionError(err instanceof Error ? err.message : 'Failed to update settings')
                      } finally {
                        setAutoScanBusy(false)
                      }
                    }}
                    disabled={autoScanBusy}
                  />
                </label>
                <p className="sources-automation-hint">
                  Wait this many seconds after the last file change before scanning to avoid repeated imports during large transfers.
                </p>
              </div>
            ) : null}
          </section>
        </div>
      </Card>
    </div>
  )
}
