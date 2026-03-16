import { useEffect, useState } from 'react'

import { getCollections } from '../api/collections'
import { disconnectGooglePhotos, getGooglePhotosStatus, pollGooglePhotosConnect, startGooglePhotosConnect, syncGooglePhotos } from '../api/googlePhotos'
import { runLocalImport, scanLocalSource } from '../api/import'
import { getSources, updateSource } from '../api/sources'
import type {
  GooglePhotosProviderStatus,
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
  googlePhotos: Awaited<ReturnType<typeof getGooglePhotosStatus>>
}

type DraftMap = Record<string, Required<Pick<SourceUpdateRequest, 'name' | 'import_path' | 'enabled'>>>
type BusyAction = 'save' | 'scan' | 'run' | 'connect' | 'poll' | 'sync' | 'disconnect' | null

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
      const [sources, collections, googlePhotos] = await Promise.all([getSources(), getCollections(), getGooglePhotosStatus()])
      return { sources, collections, googlePhotos }
    },
    [],
  )

  const [drafts, setDrafts] = useState<DraftMap>({})
  const [scanRequest, setScanRequest] = useState<LocalImportScanRequest>(emptyScanRequest)
  const [runRequest, setRunRequest] = useState<LocalImportRunRequest>(emptyRunRequest)
  const [scanResult, setScanResult] = useState<LocalImportScanResult | null>(null)
  const [runResult, setRunResult] = useState<LocalImportRunResult | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [busyAction, setBusyAction] = useState<BusyAction>(null)

  const localSources = (data?.sources ?? []).filter((source) => source.provider_type === 'local_files')
  const googlePhotos = data?.googlePhotos ?? emptyGooglePhotosStatus

  useEffect(() => {
    if (!data) {
      return
    }

    const nextLocalSources = data.sources.filter((source) => source.provider_type === 'local_files')

    setDrafts(
      Object.fromEntries(
        nextLocalSources.map((source) => [
          source.id,
          {
            name: source.name,
            import_path: source.import_path,
            enabled: source.enabled,
          },
        ]),
      ),
    )

    setScanRequest((current) => ({
      source_id:
        nextLocalSources.some((source) => source.id === current.source_id)
          ? current.source_id
          : (nextLocalSources[0]?.id ?? ''),
      max_samples: current.max_samples || 10,
    }))

    setRunRequest((current) => ({
      source_id:
        nextLocalSources.some((source) => source.id === current.source_id)
          ? current.source_id
          : (nextLocalSources[0]?.id ?? ''),
      collection_id: current.collection_id || data.collections[0]?.id || 'default-collection',
      max_samples: current.max_samples || 10,
    }))
  }, [data])

  async function handleSaveSource(source: SourceSummary) {
    const draft = drafts[source.id]
    if (!draft) {
      return
    }

    try {
      setBusyAction('save')
      setActionError(null)
      const updated = await updateSource(source.id, draft)
      setData((current) =>
        current
          ? {
              ...current,
              sources: current.sources.map((item) => (item.id === updated.id ? updated : item)),
            }
          : current,
      )
      setFeedback(`Saved ${updated.name}.`)
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : 'Could not save source settings.')
    } finally {
      setBusyAction(null)
    }
  }

  async function handleScan(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    try {
      setBusyAction('scan')
      setActionError(null)
      const result = await scanLocalSource(scanRequest)
      setScanResult(result)
      setFeedback('Scan complete.')
      void reload()
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : 'Could not scan the local source.')
    } finally {
      setBusyAction(null)
    }
  }

  async function handleRun(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    try {
      setBusyAction('run')
      setActionError(null)
      const result = await runLocalImport(runRequest)
      setRunResult(result)
      setFeedback('Import complete.')
      void reload()
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : 'Could not run the local import.')
    } finally {
      setBusyAction(null)
    }
  }

  async function handleGoogleAction(action: Exclude<BusyAction, 'save' | 'scan' | 'run' | null>) {
    const messages = {
      connect: 'Google Photos connection started.',
      poll: 'Google Photos status refreshed.',
      sync: 'Google Photos sync triggered.',
      disconnect: 'Google Photos disconnected.',
    } as const

    const errors = {
      connect: 'Could not start the Google Photos connection.',
      poll: 'Could not refresh Google Photos approval status.',
      sync: 'Could not start a Google Photos sync.',
      disconnect: 'Could not disconnect Google Photos.',
    } as const

    try {
      setBusyAction(action)
      setActionError(null)

      let nextStatus: GooglePhotosProviderStatus
      if (action === 'connect') {
        nextStatus = await startGooglePhotosConnect()
      } else if (action === 'poll') {
        nextStatus = await pollGooglePhotosConnect()
      } else if (action === 'sync') {
        nextStatus = await syncGooglePhotos()
      } else {
        nextStatus = await disconnectGooglePhotos()
      }

      setData((current) => (current ? { ...current, googlePhotos: nextStatus } : current))
      setFeedback(messages[action])

      if (action === 'sync' || action === 'disconnect') {
        void reload()
      }
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : errors[action])
    } finally {
      setBusyAction(null)
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        title="Sources & providers"
        description="Manage the local-files workflow, connect Google Photos, and keep the frame stocked with cached photos for playback."
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
          title="Google Photos"
          eyebrow="Cloud provider"
          actions={
            <span className={`pill ${googleConnectionStateClassName(googlePhotos)}`}>
              {googleConnectionStateLabel(googlePhotos)}
            </span>
          }
        >
          {!googlePhotos.provider_available ? (
            <StatusNotice
              variant="empty"
              title="Google Photos unavailable"
              detail="This frame does not have Google Photos support enabled in the current backend runtime."
            />
          ) : null}

          {googlePhotos.provider_available && !googlePhotos.provider_configured ? (
            <StatusNotice
              variant="empty"
              title="Google Photos not configured"
              detail="Add the Google Photos runtime credentials on the backend before connecting an account."
            />
          ) : null}

          {googlePhotos.error ? <StatusNotice variant="error" title="Google Photos needs attention" detail={googlePhotos.error} /> : null}

          {googlePhotos.provider_available && googlePhotos.provider_configured ? (
            <div className="form-grid">
              <p className="card-muted">
                Use Google&apos;s device approval flow on another screen, then let SPF5000 keep a local cache ready for the
                slideshow.
              </p>

              <dl className="detail-list detail-list--compact">
                <div>
                  <dt>Connection state</dt>
                  <dd>{toTitleCase(googlePhotos.connection_state)}</dd>
                </div>
                <div>
                  <dt>Cached assets</dt>
                  <dd>{formatNumber(googlePhotos.cached_asset_count)}</dd>
                </div>
                <div>
                  <dt>Last successful sync</dt>
                  <dd>{formatDateTime(googlePhotos.last_successful_sync_at)}</dd>
                </div>
              </dl>

              {googlePhotos.pending_auth ? (
                <Card title="Approve this frame" eyebrow="Device flow">
                  <p className="card-muted">
                    Open the Google verification page, enter the code below, approve access, then come back here and check
                    approval.
                  </p>
                  <div className="inline-list">
                    <a
                      href={googlePhotos.pending_auth.verification_uri}
                      target="_blank"
                      rel="noreferrer"
                      className="button button--ghost"
                    >
                      Open verification page
                    </a>
                    <span className="pill pill--warning">{googlePhotos.pending_auth.user_code}</span>
                  </div>
                  <dl className="detail-list detail-list--compact">
                    <div>
                      <dt>Verification URL</dt>
                      <dd>{googlePhotos.pending_auth.verification_uri}</dd>
                    </div>
                    <div>
                      <dt>Code expires</dt>
                      <dd>{formatDateTime(googlePhotos.pending_auth.expires_at)}</dd>
                    </div>
                    <div>
                      <dt>Check interval</dt>
                      <dd>{googlePhotos.pending_auth.interval_seconds || '—'} seconds</dd>
                    </div>
                  </dl>
                  <div className="form-actions">
                    <button
                      type="button"
                      className="button"
                      disabled={busyAction === 'poll'}
                      onClick={() => void handleGoogleAction('poll')}
                    >
                      {busyAction === 'poll' ? 'Checking…' : 'Check approval'}
                    </button>
                    <button
                      type="button"
                      className="button button--ghost"
                      disabled={busyAction === 'connect'}
                      onClick={() => void handleGoogleAction('connect')}
                    >
                      {busyAction === 'connect' ? 'Restarting…' : 'Restart connection'}
                    </button>
                  </div>
                </Card>
              ) : null}

              {googlePhotos.account ? (
                <Card title="Linked account" eyebrow="Connection">
                  <dl className="detail-list detail-list--compact">
                    <div>
                      <dt>Name</dt>
                      <dd>{googlePhotos.account.display_name ?? '—'}</dd>
                    </div>
                    <div>
                      <dt>Email</dt>
                      <dd>{googlePhotos.account.email ?? '—'}</dd>
                    </div>
                    <div>
                      <dt>Connected</dt>
                      <dd>{formatDateTime(googlePhotos.account.connected_at)}</dd>
                    </div>
                  </dl>
                </Card>
              ) : null}

              {googlePhotos.device ? (
                <Card
                  title="Google Photos device"
                  eyebrow="Frame selection"
                  actions={
                    googlePhotos.device.settings_uri ? (
                      <a href={googlePhotos.device.settings_uri} target="_blank" rel="noreferrer" className="button button--ghost">
                        Open Google Photos settings
                      </a>
                    ) : null
                  }
                >
                  <dl className="detail-list detail-list--compact">
                    <div>
                      <dt>Device name</dt>
                      <dd>{googlePhotos.device.display_name ?? '—'}</dd>
                    </div>
                    <div>
                      <dt>Media sources set</dt>
                      <dd>{googlePhotos.device.media_sources_set ? 'Selected' : 'Not selected yet'}</dd>
                    </div>
                  </dl>

                  {googlePhotos.device.selected_media_sources.length > 0 ? (
                    <ul className="simple-list">
                      {googlePhotos.device.selected_media_sources.map((source) => (
                        <li key={source.id}>
                          <div>
                            <strong>{source.name}</strong>
                            <p>{source.id}</p>
                          </div>
                          <span className="pill pill--muted">{source.type ?? 'Media source'}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="card-muted">No Google Photos media sources have been selected for this frame yet.</p>
                  )}
                </Card>
              ) : null}

              {googlePhotos.latest_sync_run ? (
                <Card title="Latest sync run" eyebrow="Provider cache">
                  <dl className="detail-list detail-list--compact">
                    <div>
                      <dt>Status</dt>
                      <dd>{toTitleCase(googlePhotos.latest_sync_run.status)}</dd>
                    </div>
                    <div>
                      <dt>Started</dt>
                      <dd>{formatDateTime(googlePhotos.latest_sync_run.started_at)}</dd>
                    </div>
                    <div>
                      <dt>Completed</dt>
                      <dd>{formatDateTime(googlePhotos.latest_sync_run.completed_at)}</dd>
                    </div>
                    <div>
                      <dt>Imported</dt>
                      <dd>{formatNumber(googlePhotos.latest_sync_run.imported_count)}</dd>
                    </div>
                    <div>
                      <dt>Updated</dt>
                      <dd>{formatNumber(googlePhotos.latest_sync_run.updated_count)}</dd>
                    </div>
                    <div>
                      <dt>Removed</dt>
                      <dd>{formatNumber(googlePhotos.latest_sync_run.removed_count)}</dd>
                    </div>
                    <div>
                      <dt>Skipped</dt>
                      <dd>{formatNumber(googlePhotos.latest_sync_run.skipped_count)}</dd>
                    </div>
                    <div>
                      <dt>Errors</dt>
                      <dd>{formatNumber(googlePhotos.latest_sync_run.error_count)}</dd>
                    </div>
                  </dl>
                  {googlePhotos.latest_sync_run.message ? <p className="card-muted">{googlePhotos.latest_sync_run.message}</p> : null}
                </Card>
              ) : null}

              {googlePhotos.warning ? (
                <div className="inline-list">
                  <span className="pill pill--warning">Warning</span>
                  <p className="card-muted">{googlePhotos.warning}</p>
                </div>
              ) : null}

              <div className="form-actions">
                {!googlePhotos.account && !googlePhotos.pending_auth ? (
                  <button
                    type="button"
                    className="button"
                    disabled={busyAction === 'connect'}
                    onClick={() => void handleGoogleAction('connect')}
                  >
                    {busyAction === 'connect' ? 'Connecting…' : 'Connect Google Photos'}
                  </button>
                ) : null}

                {googlePhotos.pending_auth ? (
                  <button
                    type="button"
                    className="button button--ghost"
                    disabled={busyAction === 'poll'}
                    onClick={() => void handleGoogleAction('poll')}
                  >
                    {busyAction === 'poll' ? 'Checking…' : 'Refresh approval status'}
                  </button>
                ) : null}

                {googlePhotos.account ? (
                  <>
                    <button
                      type="button"
                      className="button"
                      disabled={busyAction === 'sync'}
                      onClick={() => void handleGoogleAction('sync')}
                    >
                      {busyAction === 'sync' ? 'Syncing…' : 'Sync now'}
                    </button>
                    <button
                      type="button"
                      className="button button--ghost"
                      disabled={busyAction === 'disconnect'}
                      onClick={() => void handleGoogleAction('disconnect')}
                    >
                      {busyAction === 'disconnect' ? 'Disconnecting…' : 'Disconnect'}
                    </button>
                  </>
                ) : null}
              </div>
            </div>
          ) : null}
        </Card>
      ) : null}

      <div className="card-grid">
        {localSources.map((source) => {
          const draft = drafts[source.id]
          if (!draft) {
            return null
          }

          return (
            <Card key={source.id} title={source.name} eyebrow={source.provider_type}>
              <form
                className="form-grid"
                onSubmit={(event) => {
                  event.preventDefault()
                  void handleSaveSource(source)
                }}
              >
                <label>
                  <span>Name</span>
                  <input
                    type="text"
                    value={draft.name}
                    onChange={(event) =>
                      setDrafts((current) => ({
                        ...current,
                        [source.id]: {
                          ...draft,
                          name: event.target.value,
                        },
                      }))
                    }
                  />
                </label>
                <label>
                  <span>Import path</span>
                  <input
                    type="text"
                    value={draft.import_path}
                    onChange={(event) =>
                      setDrafts((current) => ({
                        ...current,
                        [source.id]: {
                          ...draft,
                          import_path: event.target.value,
                        },
                      }))
                    }
                  />
                </label>
                <label className="checkbox-field">
                  <input
                    type="checkbox"
                    checked={draft.enabled}
                    onChange={(event) =>
                      setDrafts((current) => ({
                        ...current,
                        [source.id]: {
                          ...draft,
                          enabled: event.target.checked,
                        },
                      }))
                    }
                  />
                  <span>Source enabled</span>
                </label>
                <dl className="detail-list detail-list--compact">
                  <div>
                    <dt>Assets</dt>
                    <dd>{formatNumber(source.asset_count)}</dd>
                  </div>
                  <div>
                    <dt>Last scan</dt>
                    <dd>{formatDateTime(source.last_scan_at)}</dd>
                  </div>
                  <div>
                    <dt>Last import</dt>
                    <dd>{formatDateTime(source.last_import_at)}</dd>
                  </div>
                </dl>
                <div className="form-actions">
                  <button type="submit" className="button" disabled={busyAction === 'save'}>
                    {busyAction === 'save' ? 'Saving…' : 'Save source'}
                  </button>
                </div>
              </form>
            </Card>
          )
        })}
      </div>

      <div className="two-column-grid">
        <Card title="Scan configured import path" eyebrow="Discovery">
          {localSources.length > 0 ? (
            <>
              <form className="form-grid" onSubmit={(event) => void handleScan(event)}>
                <label>
                  <span>Source</span>
                  <select
                    value={scanRequest.source_id}
                    onChange={(event) =>
                      setScanRequest((current) => ({
                        ...current,
                        source_id: event.target.value,
                      }))
                    }
                  >
                    {localSources.map((source) => (
                      <option key={source.id} value={source.id}>
                        {source.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Sample file count</span>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    value={scanRequest.max_samples}
                    onChange={(event) =>
                      setScanRequest((current) => ({
                        ...current,
                        max_samples: Number(event.target.value),
                      }))
                    }
                  />
                </label>
                <div className="form-actions">
                  <button type="submit" className="button" disabled={busyAction === 'scan'}>
                    {busyAction === 'scan' ? 'Scanning…' : 'Scan source'}
                  </button>
                </div>
              </form>

              {scanResult ? (
                <>
                  <dl className="detail-list detail-list--compact">
                    <div>
                      <dt>Discovered</dt>
                      <dd>{formatNumber(scanResult.discovered_count)}</dd>
                    </div>
                    <div>
                      <dt>Ignored</dt>
                      <dd>{formatNumber(scanResult.ignored_count)}</dd>
                    </div>
                    <div>
                      <dt>Job status</dt>
                      <dd>{scanResult.job.status}</dd>
                    </div>
                  </dl>
                  {scanResult.sample_filenames.length > 0 ? (
                    <div className="inline-list">
                      {scanResult.sample_filenames.map((file) => (
                        <span key={file} className="pill pill--muted">
                          {file}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </>
              ) : null}
            </>
          ) : (
            <StatusNotice
              variant="empty"
              title="No local source available"
              detail="Add or restore the local-files source before running a scan."
            />
          )}
        </Card>

        <Card title="Run import" eyebrow="Ingest">
          {localSources.length > 0 ? (
            <>
              <form className="form-grid" onSubmit={(event) => void handleRun(event)}>
                <label>
                  <span>Source</span>
                  <select
                    value={runRequest.source_id}
                    onChange={(event) =>
                      setRunRequest((current) => ({
                        ...current,
                        source_id: event.target.value,
                      }))
                    }
                  >
                    {localSources.map((source) => (
                      <option key={source.id} value={source.id}>
                        {source.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Target collection</span>
                  <select
                    value={runRequest.collection_id}
                    onChange={(event) =>
                      setRunRequest((current) => ({
                        ...current,
                        collection_id: event.target.value,
                      }))
                    }
                  >
                    {(data?.collections ?? []).map((collection) => (
                      <option key={collection.id} value={collection.id}>
                        {collection.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Sample file count</span>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    value={runRequest.max_samples}
                    onChange={(event) =>
                      setRunRequest((current) => ({
                        ...current,
                        max_samples: Number(event.target.value),
                      }))
                    }
                  />
                </label>
                <div className="form-actions">
                  <button type="submit" className="button" disabled={busyAction === 'run'}>
                    {busyAction === 'run' ? 'Importing…' : 'Run import'}
                  </button>
                </div>
              </form>

              {runResult ? (
                <dl className="detail-list detail-list--compact">
                  <div>
                    <dt>Imported</dt>
                    <dd>{formatNumber(runResult.imported_count)}</dd>
                  </div>
                  <div>
                    <dt>Duplicates</dt>
                    <dd>{formatNumber(runResult.duplicate_count)}</dd>
                  </div>
                  <div>
                    <dt>Errors</dt>
                    <dd>{formatNumber(runResult.error_count)}</dd>
                  </div>
                  <div>
                    <dt>Status</dt>
                    <dd>{runResult.status}</dd>
                  </div>
                </dl>
              ) : null}
            </>
          ) : (
            <StatusNotice
              variant="empty"
              title="No local source available"
              detail="Add or restore the local-files source before running an import."
            />
          )}
        </Card>
      </div>
    </div>
  )
}

const emptyGooglePhotosStatus: GooglePhotosProviderStatus = {
  provider_available: false,
  provider_configured: false,
  connection_state: 'unavailable',
  pending_auth: null,
  account: null,
  device: null,
  latest_sync_run: null,
  cached_asset_count: 0,
  last_successful_sync_at: null,
  warning: null,
  error: null,
}

function googleConnectionStateClassName(status: GooglePhotosProviderStatus): string {
  if (!status.provider_available || !status.provider_configured) {
    return 'pill--muted'
  }

  if (status.pending_auth) {
    return 'pill--warning'
  }

  return status.account ? 'pill--ok' : 'pill--muted'
}

function googleConnectionStateLabel(status: GooglePhotosProviderStatus): string {
  if (!status.provider_available) {
    return 'Unavailable'
  }

  if (!status.provider_configured) {
    return 'Not configured'
  }

  if (status.pending_auth) {
    return 'Awaiting approval'
  }

  return status.account ? 'Connected' : toTitleCase(status.connection_state)
}
