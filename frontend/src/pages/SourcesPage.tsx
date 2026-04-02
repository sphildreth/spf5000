import { useState } from 'react'

import { getAutoScanStatus, configureAutoScan, type AutoScanStatus } from '../api/autoScan'
import { getCollections } from '../api/collections'
import { runLocalImport, scanLocalSource } from '../api/import'
import { getSources, updateSource } from '../api/sources'
import type {
  LocalImportRunRequest,
  LocalImportRunResult,
  LocalImportScanRequest,
  LocalImportScanResult,
  SourceSummary,
  SourceUpdateRequest,
} from '../api/types'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { StatusNotice } from '../components/StatusNotice'
import { useAsyncData } from '../hooks/useAsyncData'
import { formatDateTime, formatNumber, toTitleCase } from '../utils/format'

interface SourcesData {
  sources: Awaited<ReturnType<typeof getSources>>
  collections: Awaited<ReturnType<typeof getCollections>>
  autoScan: AutoScanStatus
}

type DraftMap = Record<string, Required<Pick<SourceUpdateRequest, 'name' | 'import_path' | 'enabled'>>>
type BusyAction = 'save' | 'scan' | 'run' | null

const emptyScanRequest: LocalImportScanRequest = {
  source_id: '',
  max_samples: 10,
}

const emptyRunRequest: LocalImportRunRequest = {
  source_id: '',
  collection_id: '',
  max_samples: 10,
}

export function SourcesPage() {
  const { data, loading, error, reload, setData } = useAsyncData<SourcesData>(
    async () => {
      const [sources, collections, autoScan] = await Promise.all([
        getSources(),
        getCollections(),
        getAutoScanStatus(),
      ])
      return { sources, collections, autoScan }
    },
    [],
  )

  const [drafts, setDrafts] = useState<DraftMap>({})
  const [busyAction, setBusyAction] = useState<BusyAction>(null)
  const [scanRequest, setScanRequest] = useState<LocalImportScanRequest>(emptyScanRequest)
  const [runRequest, setRunRequest] = useState<LocalImportRunRequest>(emptyRunRequest)
  const [scanResult, setScanResult] = useState<LocalImportScanResult | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [autoScanConfig, setAutoScanConfig] = useState<AutoScanStatus | null>(null)
  const [autoScanBusy, setAutoScanBusy] = useState(false)

  async function handleSaveSource(source: SourceSummary) {
    const draft = drafts[source.id]
    if (!draft) return

    setBusyAction('save')
    setActionError(null)

    try {
      await updateSource(source.id, draft)
      setFeedback(`Saved changes to "${draft.name}".`)
      void reload()
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : 'Could not save source changes.')
    } finally {
      setBusyAction(null)
    }
  }

  async function handleScanSource(source: SourceSummary) {
    setBusyAction('scan')
    setActionError(null)
    setScanRequest((current) => ({ ...current, source_id: source.id }))

    try {
      const result = await scanLocalSource({ source_id: source.id, max_samples: 10 })
      setScanResult(result)
      setFeedback(`Scan found ${formatNumber(result.discovered_count)} new photos.`)
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : 'Could not scan source.')
    } finally {
      setBusyAction(null)
    }
  }

  async function handleRunImport(source: SourceSummary) {
    setBusyAction('run')
    setActionError(null)
    setRunRequest((current) => ({ ...current, source_id: source.id }))

    try {
      const payload: LocalImportRunRequest = {
        source_id: source.id,
        collection_id: runRequest.collection_id || 'default-collection',
        max_samples: runRequest.max_samples || 10,
      }
      await runLocalImport(payload)
      setFeedback(`Import started for "${source.name}".`)
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

          <div className="form-actions">
            <button
              type="button"
              className="button"
              disabled={busyAction === 'scan'}
              onClick={() => localSources[0] && void handleScanSource(localSources[0])}
            >
              {busyAction === 'scan' ? 'Scanning…' : 'Scan now'}
            </button>
            <button
              type="button"
              className="button button--ghost"
              disabled={busyAction === 'run'}
              onClick={() => localSources[0] && void handleRunImport(localSources[0])}
            >
              {busyAction === 'run' ? 'Importing…' : 'Import now'}
            </button>
          </div>

          {scanResult ? (
            <Card title="Scan results" eyebrow="Preview">
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
                <div style={{ marginTop: '1rem' }}>
                  <strong>Sample files:</strong>
                  <ul style={{ marginTop: '0.5rem', marginBottom: 0 }}>
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

        <div style={{ marginBottom: '1.5rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
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
            <span><strong>Enable scheduled scanning</strong></span>
          </label>
          <p style={{ marginLeft: '1.5rem', fontSize: '0.9rem', color: '#666' }}>
            Automatically scan and import new photos on a schedule.
          </p>
        </div>

        {data?.autoScan.auto_scan_enabled && (
          <div style={{ marginBottom: '1.5rem', marginLeft: '1.5rem' }}>
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
                style={{ width: '100%', maxWidth: '300px', marginTop: '0.25rem' }}
              />
            </label>
            <p style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.25rem' }}>
              Examples: <code>0 */4 * * *</code> (every 4 hours), <code>0 3 * * *</code> (daily at 3 AM), <code>0 * * * *</code> (every hour)
            </p>
          </div>
        )}

        <div style={{ marginBottom: '1.5rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
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
            <span><strong>Enable auto-watch</strong></span>
          </label>
          <p style={{ marginLeft: '1.5rem', fontSize: '0.9rem', color: '#666' }}>
            Automatically scan and import when new files are detected in the import folder.
          </p>
        </div>

        {data?.autoScan.auto_watch_enabled && (
          <div style={{ marginBottom: '1.5rem', marginLeft: '1.5rem' }}>
            <label>
              <span>Debounce delay (seconds)</span>
              <input
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
                style={{ width: '80px', marginLeft: '0.5rem' }}
              />
            </label>
            <p style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.25rem' }}>
              Wait this many seconds after the last file change before scanning (prevents multiple scans during large transfers).
            </p>
          </div>
        )}
      </Card>
    </div>
  )
}
