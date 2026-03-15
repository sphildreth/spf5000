import { useMemo, useState } from 'react'

import { getCollections } from '../api/collections'
import { runLocalImport, scanLocalSource } from '../api/import'
import { createSource, getSources } from '../api/sources'
import type {
  CreateSourceRequest,
  LocalImportRunRequest,
  LocalImportRunResult,
  LocalImportScanRequest,
  LocalImportScanResult,
} from '../api/types'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { StatusNotice } from '../components/StatusNotice'
import { useAsyncData } from '../hooks/useAsyncData'
import { formatDateTime, formatNumber } from '../utils/format'

interface SourcesData {
  sources: Awaited<ReturnType<typeof getSources>>
  collections: Awaited<ReturnType<typeof getCollections>>
}

const defaultSource: CreateSourceRequest = {
  name: '',
  kind: 'local',
  path: '/srv/photos',
}

const defaultScanRequest: LocalImportScanRequest = {
  path: '/srv/photos',
  recursive: true,
}

const defaultRunRequest: LocalImportRunRequest = {
  path: '/srv/photos',
  recursive: true,
  collection_id: '',
}

export function SourcesPage() {
  const { data, loading, error, reload, setData } = useAsyncData<SourcesData>(
    async () => {
      const [sources, collections] = await Promise.all([getSources(), getCollections()])
      return { sources, collections }
    },
    [],
  )

  const [sourceDraft, setSourceDraft] = useState<CreateSourceRequest>(defaultSource)
  const [scanRequest, setScanRequest] = useState<LocalImportScanRequest>(defaultScanRequest)
  const [runRequest, setRunRequest] = useState<LocalImportRunRequest>(defaultRunRequest)
  const [scanResult, setScanResult] = useState<LocalImportScanResult | null>(null)
  const [runResult, setRunResult] = useState<LocalImportRunResult | null>(null)
  const [busyAction, setBusyAction] = useState<'create' | 'scan' | 'run' | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const collectionOptions = useMemo(() => data?.collections ?? [], [data])

  async function handleCreateSource(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!sourceDraft.name.trim() || !sourceDraft.path.trim()) {
      return
    }

    try {
      setBusyAction('create')
      setActionError(null)
      const created = await createSource({
        ...sourceDraft,
        name: sourceDraft.name.trim(),
        path: sourceDraft.path.trim(),
      })
      setData((current) =>
        current
          ? {
              ...current,
              sources: [created, ...current.sources],
            }
          : current,
      )
      setFeedback(`Added source ${created.name}.`)
      setSourceDraft(defaultSource)
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : 'Could not create source.')
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
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : 'Could not scan local source.')
    } finally {
      setBusyAction(null)
    }
  }

  async function handleRun(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    try {
      setBusyAction('run')
      setActionError(null)
      const result = await runLocalImport({
        ...runRequest,
        collection_id: runRequest.collection_id || undefined,
      })
      setRunResult(result)
      setFeedback('Import run complete.')
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : 'Could not run import.')
    } finally {
      setBusyAction(null)
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        title="Sources & local import"
        description="Manage source definitions, scan a directory, and run the local importer without leaving the admin UI."
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

      <div className="three-column-grid">
        <Card title="Add source" eyebrow="Definition">
          <form className="form-grid" onSubmit={(event) => void handleCreateSource(event)}>
            <label>
              <span>Name</span>
              <input
                type="text"
                value={sourceDraft.name}
                onChange={(event) => setSourceDraft((current) => ({ ...current, name: event.target.value }))}
              />
            </label>
            <label>
              <span>Kind</span>
              <select
                value={sourceDraft.kind}
                onChange={(event) => setSourceDraft((current) => ({ ...current, kind: event.target.value }))}
              >
                <option value="local">Local</option>
                <option value="provider">Provider</option>
              </select>
            </label>
            <label>
              <span>Path</span>
              <input
                type="text"
                value={sourceDraft.path}
                onChange={(event) => setSourceDraft((current) => ({ ...current, path: event.target.value }))}
              />
            </label>
            <div className="form-actions">
              <button type="submit" className="button" disabled={busyAction == 'create'}>
                {busyAction === 'create' ? 'Adding…' : 'Add source'}
              </button>
            </div>
          </form>
        </Card>

        <Card title="Scan local path" eyebrow="Discovery">
          <form className="form-grid" onSubmit={(event) => void handleScan(event)}>
            <label>
              <span>Directory path</span>
              <input
                type="text"
                value={scanRequest.path}
                onChange={(event) => setScanRequest((current) => ({ ...current, path: event.target.value }))}
              />
            </label>
            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={scanRequest.recursive}
                onChange={(event) =>
                  setScanRequest((current) => ({
                    ...current,
                    recursive: event.target.checked,
                  }))
                }
              />
              <span>Include nested folders</span>
            </label>
            <div className="form-actions">
              <button type="submit" className="button" disabled={busyAction === 'scan'}>
                {busyAction === 'scan' ? 'Scanning…' : 'Scan'}
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
                  <dt>Skipped</dt>
                  <dd>{formatNumber(scanResult.skipped_count)}</dd>
                </div>
              </dl>
              {scanResult.sample_files.length > 0 ? (
                <div className="inline-list">
                  {scanResult.sample_files.slice(0, 4).map((file) => (
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
              <span>Directory path</span>
              <input
                type="text"
                value={runRequest.path}
                onChange={(event) => setRunRequest((current) => ({ ...current, path: event.target.value }))}
              />
            </label>
            <label>
              <span>Target collection</span>
              <select
                value={runRequest.collection_id ?? ''}
                onChange={(event) =>
                  setRunRequest((current) => ({
                    ...current,
                    collection_id: event.target.value,
                  }))
                }
              >
                <option value="">None</option>
                {collectionOptions.map((collection) => (
                  <option key={collection.id} value={collection.id}>
                    {collection.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={runRequest.recursive}
                onChange={(event) =>
                  setRunRequest((current) => ({
                    ...current,
                    recursive: event.target.checked,
                  }))
                }
              />
              <span>Include nested folders</span>
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
                <dt>Failed</dt>
                <dd>{formatNumber(runResult.failed_count)}</dd>
              </div>
            </dl>
          ) : null}
        </Card>
      </div>

      <Card title="Configured sources" eyebrow="Available providers">
        {data && data.sources.length > 0 ? (
          <div className="card-grid">
            {data.sources.map((source) => (
              <article key={source.id} className="source-card">
                <div className="source-card-row">
                  <div>
                    <h3>{source.name}</h3>
                    <p>{source.path ?? source.kind}</p>
                  </div>
                  <span className={`pill pill--${source.enabled ? 'ok' : 'muted'}`}>{source.status}</span>
                </div>
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
                {source.detail ? <p className="card-muted">{source.detail}</p> : null}
              </article>
            ))}
          </div>
        ) : (
          <StatusNotice
            variant="empty"
            title="No sources configured"
            detail="Add a source above and use the scan/import tools to populate the library."
          />
        )}
      </Card>
    </div>
  )
}
