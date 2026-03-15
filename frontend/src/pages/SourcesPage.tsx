import { useEffect, useState } from 'react'

import { getCollections } from '../api/collections'
import { runLocalImport, scanLocalSource } from '../api/import'
import { getSources, updateSource } from '../api/sources'
import type { LocalImportRunRequest, LocalImportRunResult, LocalImportScanRequest, LocalImportScanResult, SourceSummary, SourceUpdateRequest } from '../api/types'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { StatusNotice } from '../components/StatusNotice'
import { useAsyncData } from '../hooks/useAsyncData'
import { formatDateTime, formatNumber } from '../utils/format'

interface SourcesData {
  sources: Awaited<ReturnType<typeof getSources>>
  collections: Awaited<ReturnType<typeof getCollections>>
}

type DraftMap = Record<string, Required<Pick<SourceUpdateRequest, 'name' | 'import_path' | 'enabled'>>>

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
      const [sources, collections] = await Promise.all([getSources(), getCollections()])
      return { sources, collections }
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
  const [busyAction, setBusyAction] = useState<'save' | 'scan' | 'run' | null>(null)

  useEffect(() => {
    if (!data) {
      return
    }

    setDrafts(
      Object.fromEntries(
        data.sources.map((source) => [
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
      source_id: current.source_id || data.sources[0]?.id || '',
      max_samples: current.max_samples || 10,
    }))

    setRunRequest((current) => ({
      source_id: current.source_id || data.sources[0]?.id || '',
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

  return (
    <div className="page-stack">
      <PageHeader
        title="Sources & local import"
        description="Manage the local-files source, scan its configured directory, and import images into a collection for playback."
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

      {!loading && !error && (data?.sources.length ?? 0) === 0 ? (
        <StatusNotice
          variant="empty"
          title="No sources configured"
          detail="The backend should bootstrap a default local-files source automatically."
        />
      ) : null}

      <div className="card-grid">
        {(data?.sources ?? []).map((source) => {
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
                {(data?.sources ?? []).map((source) => (
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
        </Card>

        <Card title="Run import" eyebrow="Ingest">
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
                {(data?.sources ?? []).map((source) => (
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
        </Card>
      </div>
    </div>
  )
}
