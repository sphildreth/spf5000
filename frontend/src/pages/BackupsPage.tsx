import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'

import { getCollectionExportPath, getDatabaseBackupExportPath, importDatabaseBackup } from '../api/backups'
import { getCollections } from '../api/collections'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { StatusNotice } from '../components/StatusNotice'
import { useSession } from '../context/SessionContext'
import { useAsyncData } from '../hooks/useAsyncData'
import { formatBytes, formatNumber } from '../utils/format'
import { setBackupRestoreFlash } from '../utils/sessionFlash'

export function BackupsPage() {
  const { refresh } = useSession()
  const { data: collections, loading, error, reload } = useAsyncData(getCollections, [])
  const [selectedCollectionId, setSelectedCollectionId] = useState('')
  const [collectionExportFeedback, setCollectionExportFeedback] = useState<string | null>(null)
  const [collectionExportError, setCollectionExportError] = useState<string | null>(null)
  const [restoreFile, setRestoreFile] = useState<File | null>(null)
  const [restoreConfirmed, setRestoreConfirmed] = useState(false)
  const [restoreError, setRestoreError] = useState<string | null>(null)
  const [restoring, setRestoring] = useState(false)
  const restoreFileInputRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    if (!collections || collections.length === 0) {
      setSelectedCollectionId('')
      return
    }

    if (!collections.some((collection) => collection.id === selectedCollectionId)) {
      setSelectedCollectionId(collections[0].id)
    }
  }, [collections, selectedCollectionId])

  const selectedCollection = useMemo(
    () => (collections ?? []).find((collection) => collection.id === selectedCollectionId) ?? null,
    [collections, selectedCollectionId],
  )
  const collectionHasNoAssets = selectedCollection?.asset_count === 0
  const collectionExportDisabled = !selectedCollectionId || collectionHasNoAssets

  function handleDatabaseExport() {
    startArchiveDownload(getDatabaseBackupExportPath())
  }

  function handleCollectionExport() {
    if (!selectedCollection) {
      setCollectionExportFeedback(null)
      setCollectionExportError('Choose a collection before exporting original media.')
      return
    }

    if (selectedCollection.asset_count === 0) {
      setCollectionExportFeedback(null)
      setCollectionExportError('The selected collection has no original media to export.')
      return
    }

    setCollectionExportError(null)
    setCollectionExportFeedback(`Collection export download started for ${selectedCollection.name}.`)
    startArchiveDownload(getCollectionExportPath(selectedCollection.id))
  }

  async function handleRestore(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!restoreFile) {
      setRestoreError('Choose a database backup ZIP before restoring.')
      return
    }

    if (!restoreConfirmed) {
      setRestoreError('Confirm that this restore will replace the current SPF5000 database before continuing.')
      return
    }

    try {
      setRestoring(true)
      setRestoreError(null)
      const result = await importDatabaseBackup(restoreFile)
      setBackupRestoreFlash(buildRestoreFlashMessage(result.message, result.media_restored))
      setRestoreFile(null)
      setRestoreConfirmed(false)
      if (restoreFileInputRef.current) {
        restoreFileInputRef.current.value = ''
      }
      await refresh()
    } catch (caught) {
      setRestoreError(caught instanceof Error ? caught.message : 'Could not restore the selected database backup.')
    } finally {
      setRestoring(false)
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        title="Backups"
        description="Download a database backup ZIP, restore a database backup ZIP, or export original media from a collection. Database backup restores settings, state, and metadata; collection export is the media-export path."
        actions={
          <button type="button" className="button button--ghost" onClick={() => void reload()}>
            Refresh
          </button>
        }
      />

      {loading ? <StatusNotice variant="loading" title="Loading collections…" /> : null}
      {error ? <StatusNotice variant="error" title="Could not load collections" detail={error} /> : null}
      {collectionExportFeedback ? (
        <StatusNotice
          variant="success"
          title="Collection export started"
          detail={collectionExportFeedback}
        />
      ) : null}
      {collectionExportError ? (
        <StatusNotice variant="error" title="Could not start collection export" detail={collectionExportError} />
      ) : null}
      {restoreError ? <StatusNotice variant="error" title="Database restore failed" detail={restoreError} /> : null}

      <div className="two-column-grid">
        <Card title="Database backup" eyebrow="State and metadata">
          <p className="card-muted">
            Use this ZIP to capture the SPF5000 database, including settings, session state, collections, and asset
            metadata. This is not a full original-media restore on its own.
          </p>
          <div className="form-actions">
            <button type="button" className="button" onClick={handleDatabaseExport}>
              Download database backup ZIP
            </button>
          </div>
        </Card>

        <Card title="Collection export" eyebrow="Original media">
          <div className="form-grid">
            <label>
              <span>Collection</span>
              <select
                value={selectedCollectionId}
                onChange={(event) => {
                  setSelectedCollectionId(event.target.value)
                  setCollectionExportFeedback(null)
                  setCollectionExportError(null)
                }}
                disabled={(collections?.length ?? 0) === 0}
              >
                {(collections ?? []).map((collection) => (
                  <option key={collection.id} value={collection.id}>
                    {collection.name}
                  </option>
                ))}
              </select>
            </label>

            <dl className="detail-list detail-list--compact">
              <div>
                <dt>Assets</dt>
                <dd>{formatNumber(selectedCollection?.asset_count)}</dd>
              </div>
              <div>
                <dt>Export scope</dt>
                <dd>Original media only</dd>
              </div>
            </dl>

            <p className="card-muted">
              Collection export packages the original image files for one collection. Use this when you need the media
              itself, not just the database metadata.
            </p>

            <div className="form-actions">
              <button type="button" className="button" onClick={handleCollectionExport} disabled={collectionExportDisabled}>
                Download collection ZIP
              </button>
            </div>
          </div>
        </Card>
      </div>

      <Card title="Restore database backup" eyebrow="Destructive action">
        <form className="form-grid" onSubmit={(event) => void handleRestore(event)}>
          <label>
            <span>Backup ZIP file</span>
            <input
              ref={restoreFileInputRef}
              type="file"
              accept=".zip,application/zip"
              onChange={(event) => {
                const nextFile = event.target.files?.[0] ?? null
                setRestoreFile(nextFile)
                setRestoreError(null)
              }}
            />
          </label>

          {restoreFile ? (
            <div>
              <span className="pill pill--muted">{restoreFile.name}</span>{' '}
              <span className="pill pill--muted">{formatBytes(restoreFile.size)}</span>
            </div>
          ) : null}

          <p className="card-muted">
            Restoring a database backup replaces the current SPF5000 database, including settings, collections, and
            stored metadata. It does not restore original media files by itself.
          </p>

          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={restoreConfirmed}
              onChange={(event) => setRestoreConfirmed(event.target.checked)}
            />
            <span>I understand this will replace the current SPF5000 database.</span>
          </label>

          <div className="form-actions">
            <button type="submit" className="button" disabled={restoring || !restoreFile || !restoreConfirmed}>
              {restoring ? 'Restoring…' : 'Restore database backup'}
            </button>
          </div>
        </form>
      </Card>
    </div>
  )
}

function startArchiveDownload(path: string) {
  const link = document.createElement('a')
  link.href = path
  link.target = '_blank'
  link.rel = 'noopener noreferrer'
  document.body.append(link)
  link.click()
  link.remove()
}

function buildRestoreFlashMessage(message: string, mediaRestored: boolean): string {
  const baseMessage = message.trim() || 'Database backup restored. Sign in again to continue.'
  if (mediaRestored) {
    return baseMessage
  }
  const normalized = baseMessage.toLowerCase()
  if (normalized.includes('media') && normalized.includes('not restored')) {
    return baseMessage
  }

  const mediaNote = 'Original media files were not restored. Use collection export when you need the media-export path.'
  if (/[.!?]$/.test(baseMessage)) {
    return `${baseMessage} ${mediaNote}`
  }

  return `${baseMessage}. ${mediaNote}`
}
