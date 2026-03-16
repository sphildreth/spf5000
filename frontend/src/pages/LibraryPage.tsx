import { useEffect, useMemo, useRef, useState } from 'react'

import { getAssets, uploadAssets } from '../api/assets'
import { getCollections } from '../api/collections'
import type { AssetUploadSummary, CollectionSummary } from '../api/types'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { StatusNotice } from '../components/StatusNotice'
import { useAsyncData } from '../hooks/useAsyncData'
import { formatBytes, formatDateTime, formatDimensions, formatNumber } from '../utils/format'

const LOCAL_UPLOAD_SOURCE_ID = 'default-local-files'
const INITIAL_COLLECTION_FILTER = 'all'

export function LibraryPage() {
  const {
    data: assets,
    loading: assetsLoading,
    error: assetsError,
    reload: reloadAssets,
  } = useAsyncData(getAssets, [])
  const {
    data: collections,
    loading: collectionsLoading,
    error: collectionsError,
    reload: reloadCollections,
  } = useAsyncData(getCollections, [])
  const [query, setQuery] = useState('')
  const [collectionFilter, setCollectionFilter] = useState(INITIAL_COLLECTION_FILTER)
  const [uploadCollectionId, setUploadCollectionId] = useState('')
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [uploadFeedback, setUploadFeedback] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const uploadableCollections = useMemo(
    () => (collections ?? []).filter((collection) => isUploadableCollection(collection)),
    [collections],
  )

  useEffect(() => {
    if (!uploadableCollections.length) {
      return
    }
    if (!uploadableCollections.some((collection) => collection.id === uploadCollectionId)) {
      setUploadCollectionId(uploadableCollections[0].id)
    }
  }, [uploadCollectionId, uploadableCollections])

  const selectedUploadBytes = useMemo(
    () => selectedFiles.reduce((total, file) => total + file.size, 0),
    [selectedFiles],
  )

  const filteredAssets = useMemo(() => {
    const sourceAssets = assets ?? []
    const normalizedQuery = query.trim().toLowerCase()

    return sourceAssets.filter((asset) => {
      if (collectionFilter !== INITIAL_COLLECTION_FILTER && !asset.collection_ids.includes(collectionFilter)) {
        return false
      }

      if (!normalizedQuery) {
        return true
      }

      const names = asset.collection_names.length > 0 ? asset.collection_names : asset.collection_ids
      const haystack = [asset.title, asset.filename, asset.source_name, ...names]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()

      return haystack.includes(normalizedQuery)
    })
  }, [assets, collectionFilter, query])

  async function handleRefresh() {
    await Promise.allSettled([reloadAssets(), reloadCollections()])
  }

  async function handleUpload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (selectedFiles.length === 0) {
      setUploadError('Choose one or more image files before uploading.')
      return
    }
    if (!uploadCollectionId) {
      setUploadError('Select a destination collection before uploading.')
      return
    }

    try {
      setUploading(true)
      setUploadError(null)
      setUploadFeedback(null)
      const summary = await uploadAssets(selectedFiles, uploadCollectionId)
      const collectionName =
        uploadableCollections.find((collection) => collection.id === summary.collection_id)?.name ?? 'the selected collection'
      setUploadFeedback(buildUploadFeedback(summary, collectionName))
      setUploadError(summary.errors.length > 0 ? summary.errors.join(' ') : null)
      clearSelectedFiles()
      await Promise.allSettled([reloadAssets(), reloadCollections()])
    } catch (caught) {
      setUploadError(caught instanceof Error ? caught.message : 'Could not upload the selected files.')
    } finally {
      setUploading(false)
    }
  }

  function clearSelectedFiles() {
    setSelectedFiles([])
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        title="Library"
        description="Upload photos into local collections and review the cached assets the slideshow depends on."
        actions={
          <button type="button" className="button button--ghost" onClick={() => void handleRefresh()}>
            Refresh
          </button>
        }
      />

      {uploadFeedback ? <StatusNotice variant="success" title={uploadFeedback} /> : null}
      {uploadError ? <StatusNotice variant="error" title="Upload finished with issues" detail={uploadError} /> : null}
      {collectionsError ? <StatusNotice variant="error" title="Could not load collections" detail={collectionsError} /> : null}

      <div className="two-column-grid">
        <Card title="Upload photos" eyebrow="Admin upload">
          <form className="form-grid" onSubmit={(event) => void handleUpload(event)}>
            <label>
              <span>Destination collection</span>
              <select
                value={uploadCollectionId}
                onChange={(event) => setUploadCollectionId(event.target.value)}
                disabled={collectionsLoading || uploadableCollections.length === 0 || uploading}
              >
                {uploadableCollections.map((collection) => (
                  <option key={collection.id} value={collection.id}>
                    {collection.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Choose image files</span>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                multiple
                onChange={(event) => {
                  setSelectedFiles(Array.from(event.target.files ?? []))
                  setUploadFeedback(null)
                  setUploadError(null)
                }}
              />
            </label>

            {selectedFiles.length > 0 ? (
              <>
                <div className="toolbar">
                  <span className="pill pill--muted">{formatNumber(selectedFiles.length)} selected</span>
                  <span className="pill pill--muted">{formatBytes(selectedUploadBytes)}</span>
                </div>
                <div className="inline-list">
                  {selectedFiles.slice(0, 6).map((file) => (
                    <span key={`${file.name}-${file.lastModified}-${file.size}`} className="pill pill--muted">
                      {file.name}
                    </span>
                  ))}
                  {selectedFiles.length > 6 ? (
                    <span className="pill pill--muted">+{formatNumber(selectedFiles.length - 6)} more</span>
                  ) : null}
                </div>
              </>
            ) : (
              <p className="card-muted">
                Select one or more JPEG, PNG, WebP, BMP, GIF, or TIFF images. SPF5000 deduplicates uploads and
                regenerates the same thumbnails and display variants used everywhere else.
              </p>
            )}

            <div className="form-actions">
              <button
                type="submit"
                className="button"
                disabled={uploading || selectedFiles.length === 0 || uploadableCollections.length === 0}
              >
                {uploading ? 'Uploading…' : 'Upload selected photos'}
              </button>
              <button
                type="button"
                className="button button--ghost"
                onClick={clearSelectedFiles}
                disabled={uploading || selectedFiles.length === 0}
              >
                Clear selection
              </button>
            </div>
          </form>

          {!collectionsLoading && uploadableCollections.length === 0 ? (
            <StatusNotice
              variant="empty"
              title="No local collection is available for uploads"
              detail="Create or reactivate a local collection on the Collections page first."
            />
          ) : null}
        </Card>

        <Card title="Overview" eyebrow="At a glance">
          <dl className="detail-list">
            <div>
              <dt>Total assets</dt>
              <dd>{formatNumber(assets?.length)}</dd>
            </div>
            <div>
              <dt>Shown after filters</dt>
              <dd>{formatNumber(filteredAssets.length)}</dd>
            </div>
            <div>
              <dt>Upload destinations</dt>
              <dd>{formatNumber(uploadableCollections.length)}</dd>
            </div>
          </dl>
          <p className="card-muted">
            Admin uploads land in the same managed local library as scan imports and provider syncs, so the display route
            keeps reading cached files instead of anything live.
          </p>
        </Card>
      </div>

      <Card title="Asset browser" eyebrow="Local cache">
        <div className="toolbar">
          <label className="search-field">
            <span>Search</span>
            <input
              type="search"
              placeholder="Find by title, file, source, or collection"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <label className="toolbar-field">
            <span>Collection</span>
            <select value={collectionFilter} onChange={(event) => setCollectionFilter(event.target.value)}>
              <option value={INITIAL_COLLECTION_FILTER}>All collections</option>
              {(collections ?? []).map((collection) => (
                <option key={collection.id} value={collection.id}>
                  {collection.name}
                </option>
              ))}
            </select>
          </label>
          <span className="pill pill--muted">{formatNumber(filteredAssets.length)} shown</span>
        </div>

        {assetsLoading ? <StatusNotice variant="loading" title="Loading assets…" /> : null}
        {assetsError ? <StatusNotice variant="error" title="Could not load assets" detail={assetsError} /> : null}
        {!assetsLoading && !assetsError && filteredAssets.length === 0 ? (
          <StatusNotice
            variant="empty"
            title="No assets match the current filters"
            detail="Uploaded, scanned, or synced images will appear here once they exist in the local library."
          />
        ) : null}

        <div className="asset-grid">
          {filteredAssets.map((asset) => {
            const collectionLabels = asset.collection_names.length > 0 ? asset.collection_names : asset.collection_ids
            return (
              <article key={asset.id} className="asset-card">
                <div className="asset-preview">
                  {asset.thumbnail_url || asset.image_url ? (
                    <img src={asset.thumbnail_url ?? asset.image_url} alt={asset.title} loading="lazy" />
                  ) : (
                    <div className="asset-preview-placeholder">No preview</div>
                  )}
                </div>
                <div className="asset-card-body">
                  <div>
                    <h3>{asset.title}</h3>
                    <p>{asset.filename}</p>
                  </div>
                  <dl className="detail-list detail-list--compact">
                    <div>
                      <dt>Dimensions</dt>
                      <dd>{formatDimensions(asset.width, asset.height)}</dd>
                    </div>
                    <div>
                      <dt>Source</dt>
                      <dd>{asset.source_name ?? asset.source_id ?? '—'}</dd>
                    </div>
                    <div>
                      <dt>Updated</dt>
                      <dd>{formatDateTime(asset.updated_at ?? asset.imported_at)}</dd>
                    </div>
                  </dl>
                  <div className="inline-list">
                    {collectionLabels.map((name) => (
                      <span key={`${asset.id}-${name}`} className="pill pill--muted">
                        {name}
                      </span>
                    ))}
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      </Card>
    </div>
  )
}

function isUploadableCollection(collection: CollectionSummary): boolean {
  return !collection.source_id || collection.source_id === LOCAL_UPLOAD_SOURCE_ID
}

function buildUploadFeedback(summary: AssetUploadSummary, collectionName: string): string {
  const parts: string[] = []

  if (summary.imported_count > 0) {
    parts.push(`Imported ${formatCount(summary.imported_count, 'new photo')} into ${collectionName}.`)
  }
  if (summary.duplicate_count > 0) {
    parts.push(`${formatCount(summary.duplicate_count, 'duplicate')} already existed in the library.`)
  }
  if (summary.imported_count === 0 && summary.duplicate_count === 0 && summary.error_count === 0) {
    parts.push('No files were processed.')
  }

  return parts.join(' ')
}

function formatCount(value: number, singular: string): string {
  return `${formatNumber(value)} ${value === 1 ? singular : `${singular}s`}`
}
