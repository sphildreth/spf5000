import { useEffect, useMemo, useRef, useState } from 'react'

import { getAssets, removeAssetFromCollection, removeAssetsFromCollection, uploadAssets } from '../api/assets'
import { getCollections } from '../api/collections'
import type { AssetCollectionBulkDeleteSummary, AssetSummary, AssetUploadSummary, CollectionSummary } from '../api/types'
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
  const [selectedAssetIds, setSelectedAssetIds] = useState<string[]>([])
  const [uploading, setUploading] = useState(false)
  const [bulkDeleting, setBulkDeleting] = useState(false)
  const [uploadFeedback, setUploadFeedback] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [assetActionFeedback, setAssetActionFeedback] = useState<{ title: string; detail?: string } | null>(null)
  const [assetActionError, setAssetActionError] = useState<{ title: string; detail?: string } | null>(null)
  const [removingMembershipKey, setRemovingMembershipKey] = useState<string | null>(null)
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

  const collectionNamesById = useMemo(
    () => new Map((collections ?? []).map((collection) => [collection.id, collection.name])),
    [collections],
  )
  const selectedAssetIdSet = useMemo(() => new Set(selectedAssetIds), [selectedAssetIds])
  const isCollectionScopedFilter = collectionFilter !== INITIAL_COLLECTION_FILTER
  const activeCollectionName =
    (collections ?? []).find((collection) => collection.id === collectionFilter)?.name ?? collectionFilter

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
  const allVisibleAssetsSelected =
    isCollectionScopedFilter && filteredAssets.length > 0 && filteredAssets.every((asset) => selectedAssetIdSet.has(asset.id))
  const assetSelectionDisabled = bulkDeleting || removingMembershipKey !== null

  useEffect(() => {
    setSelectedAssetIds((current) => (current.length > 0 ? [] : current))
  }, [collectionFilter, filteredAssets, query])

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
      setAssetActionError(null)
      setAssetActionFeedback(null)
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

  async function handleRemoveFromCollection(assetId: string, collectionId: string, assetTitle: string, collectionName: string) {
    if (!window.confirm(`Remove "${assetTitle}" from ${collectionName}?`)) {
      return
    }

    const membershipKey = `${assetId}:${collectionId}`
    try {
      setRemovingMembershipKey(membershipKey)
      setAssetActionError(null)
      setAssetActionFeedback(null)
      setUploadError(null)
      setUploadFeedback(null)
      await removeAssetFromCollection(assetId, collectionId)
      setSelectedAssetIds((current) => current.filter((id) => id !== assetId))
      setAssetActionFeedback({
        title: `Removed "${assetTitle}" from ${collectionName}.`,
      })
      await Promise.allSettled([reloadAssets(), reloadCollections()])
    } catch (caught) {
      setAssetActionError({
        title: 'Could not remove photo',
        detail: caught instanceof Error ? caught.message : 'Could not remove the photo from the collection.',
      })
    } finally {
      setRemovingMembershipKey(null)
    }
  }

  async function handleBulkDelete() {
    if (!isCollectionScopedFilter) {
      setAssetActionFeedback(null)
      setAssetActionError({
        title: 'Choose a specific collection first',
        detail: 'Bulk removal only works when the browser is filtered to one collection.',
      })
      return
    }

    const selectedAssets = filteredAssets.filter((asset) => selectedAssetIdSet.has(asset.id))
    if (selectedAssets.length === 0) {
      setAssetActionFeedback(null)
      setAssetActionError({
        title: 'No photos selected',
        detail: 'Select one or more visible photos before trying to remove them from the collection.',
      })
      return
    }

    const confirmationTarget = activeCollectionName || 'the selected collection'
    if (
      !window.confirm(
        `Remove ${formatCount(selectedAssets.length, 'selected photo')} from ${confirmationTarget}? This only removes the collection membership.`,
      )
    ) {
      return
    }

    try {
      setBulkDeleting(true)
      setAssetActionError(null)
      setAssetActionFeedback(null)
      setUploadError(null)
      setUploadFeedback(null)

      const summary = await removeAssetsFromCollection(
        selectedAssets.map((asset) => asset.id),
        collectionFilter,
      )
      const failureDetail = buildBulkDeleteFailureDetail(summary, selectedAssets)

      if (summary.removed_count > 0) {
        const detailParts: string[] = []
        if (summary.deactivated_count > 0) {
          detailParts.push(`${formatCount(summary.deactivated_count, 'photo')} no longer belongs to any collection and was deactivated.`)
        }
        if (summary.errors.length > 0) {
          detailParts.push(`${formatCount(summary.errors.length, 'photo')} could not be removed in the same request.`)
        }

        setAssetActionFeedback({
          title: `Removed ${formatCount(summary.removed_count, 'photo')} from ${confirmationTarget}.`,
          detail: detailParts.length > 0 ? detailParts.join(' ') : undefined,
        })
      } else {
        setAssetActionFeedback(null)
      }

      if (summary.errors.length > 0) {
        setAssetActionError({
          title:
            summary.removed_count > 0 ? 'Some selected photos could not be removed' : 'Could not remove selected photos',
          detail: failureDetail,
        })
      } else {
        setAssetActionError(null)
      }

      setSelectedAssetIds([])
      await Promise.allSettled([reloadAssets(), reloadCollections()])
    } catch (caught) {
      setAssetActionFeedback(null)
      setAssetActionError({
        title: 'Could not remove selected photos',
        detail: caught instanceof Error ? caught.message : 'The selected photos could not be removed from the collection.',
      })
    } finally {
      setBulkDeleting(false)
    }
  }

  function clearSelectedFiles() {
    setSelectedFiles([])
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  function toggleAssetSelection(assetId: string) {
    setSelectedAssetIds((current) =>
      current.includes(assetId) ? current.filter((existingId) => existingId !== assetId) : [...current, assetId],
    )
  }

  function clearSelectedAssets() {
    setSelectedAssetIds([])
  }

  function selectAllVisibleAssets() {
    if (!isCollectionScopedFilter) {
      return
    }
    setSelectedAssetIds(filteredAssets.map((asset) => asset.id))
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
      {assetActionFeedback ? (
        <StatusNotice variant="success" title={assetActionFeedback.title} detail={assetActionFeedback.detail} />
      ) : null}
      {assetActionError ? (
        <StatusNotice variant="error" title={assetActionError.title} detail={assetActionError.detail} />
      ) : null}
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

        <div className="asset-bulk-bar">
          <div className="asset-bulk-bar__summary">
            <strong>
              {isCollectionScopedFilter
                ? `Bulk remove from ${activeCollectionName || 'the selected collection'}`
                : 'Bulk remove requires a collection filter'}
            </strong>
            <span className="pill pill--muted">{formatNumber(selectedAssetIds.length)} selected</span>
          </div>
          {isCollectionScopedFilter ? (
            <div className="button-row">
              <button
                type="button"
                className="button button--ghost"
                onClick={selectAllVisibleAssets}
                disabled={assetSelectionDisabled || filteredAssets.length === 0 || allVisibleAssetsSelected}
              >
                Select all shown
              </button>
              <button
                type="button"
                className="button button--ghost"
                onClick={clearSelectedAssets}
                disabled={assetSelectionDisabled || selectedAssetIds.length === 0}
              >
                Clear selection
              </button>
              <button
                type="button"
                className="button"
                onClick={() => void handleBulkDelete()}
                disabled={assetSelectionDisabled || selectedAssetIds.length === 0}
              >
                {bulkDeleting ? 'Removing selected photos…' : 'Remove selected photos'}
              </button>
            </div>
          ) : (
            <p className="asset-bulk-bar__copy">
              Choose a specific collection to multi-select visible photos and remove them together.
            </p>
          )}
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
            const collectionIds = asset.collection_ids
            const collectionLabels = collectionIds.map(
              (collectionId, index) => asset.collection_names[index] ?? collectionNamesById.get(collectionId) ?? collectionId,
            )
            const isSelected = selectedAssetIdSet.has(asset.id)
            return (
              <article key={asset.id} className={`asset-card${isSelected ? ' asset-card--selected' : ''}`}>
                <div className="asset-preview">
                  {isCollectionScopedFilter ? (
                    <label className="asset-selection-toggle">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleAssetSelection(asset.id)}
                        disabled={assetSelectionDisabled}
                      />
                      <span>Select</span>
                    </label>
                  ) : null}
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
                  <div className="asset-collection-actions">
                    {collectionIds.map((collectionId, index) => {
                      if (collectionFilter !== INITIAL_COLLECTION_FILTER && collectionFilter !== collectionId) {
                        return null
                      }

                      const collectionName = collectionLabels[index] ?? collectionId
                      const membershipKey = `${asset.id}:${collectionId}`
                      const isRemoving = removingMembershipKey === membershipKey

                      return (
                        <button
                          key={membershipKey}
                          type="button"
                          className="button button--ghost asset-remove-button"
                          onClick={() => void handleRemoveFromCollection(asset.id, collectionId, asset.title, collectionName)}
                          disabled={isRemoving || bulkDeleting}
                        >
                          {isRemoving ? `Removing from ${collectionName}…` : `Remove from ${collectionName}`}
                        </button>
                      )
                    })}
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

function buildBulkDeleteFailureDetail(summary: AssetCollectionBulkDeleteSummary, selectedAssets: AssetSummary[]): string {
  const selectedAssetsById = new Map(selectedAssets.map((asset) => [asset.id, asset]))
  const details = summary.errors.slice(0, 3).map((failure) => {
    const asset = selectedAssetsById.get(failure.asset_id)
    const label = asset?.title || asset?.filename || failure.asset_id
    return `${label}: ${failure.reason}`
  })

  if (summary.errors.length > 3) {
    details.push(`+${formatNumber(summary.errors.length - 3)} more.`)
  }

  return details.join(' ')
}

function formatCount(value: number, singular: string): string {
  return `${formatNumber(value)} ${value === 1 ? singular : `${singular}s`}`
}
