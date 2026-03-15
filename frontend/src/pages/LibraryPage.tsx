import { useMemo, useState } from 'react'

import { getAssets } from '../api/assets'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { StatusNotice } from '../components/StatusNotice'
import { useAsyncData } from '../hooks/useAsyncData'
import { formatDateTime, formatDimensions, formatNumber } from '../utils/format'

export function LibraryPage() {
  const { data, loading, error, reload } = useAsyncData(getAssets, [])
  const [query, setQuery] = useState('')

  const filteredAssets = useMemo(() => {
    const assets = data ?? []
    const normalizedQuery = query.trim().toLowerCase()

    if (!normalizedQuery) {
      return assets
    }

    return assets.filter((asset) => {
      const haystack = [asset.title, asset.filename, asset.source_name, ...asset.collection_names]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()

      return haystack.includes(normalizedQuery)
    })
  }, [data, query])

  return (
    <div className="page-stack">
      <PageHeader
        title="Library"
        description="A lightweight view of cached assets and the metadata the slideshow depends on."
        actions={
          <button type="button" className="button button--ghost" onClick={() => void reload()}>
            Refresh
          </button>
        }
      />

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
          <span className="pill pill--muted">{formatNumber(filteredAssets.length)} shown</span>
        </div>

        {loading ? <StatusNotice variant="loading" title="Loading assets…" /> : null}
        {error ? <StatusNotice variant="error" title="Could not load assets" detail={error} /> : null}
        {!loading && !error && filteredAssets.length === 0 ? (
          <StatusNotice
            variant="empty"
            title="No assets yet"
            detail="Imported images will appear here once the local scan and import flows run."
          />
        ) : null}

        <div className="asset-grid">
          {filteredAssets.map((asset) => (
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
                    <dd>{formatDateTime(asset.updated_at ?? asset.created_at)}</dd>
                  </div>
                </dl>
                <div className="inline-list">
                  {asset.collection_names.map((name) => (
                    <span key={name} className="pill pill--muted">
                      {name}
                    </span>
                  ))}
                </div>
              </div>
            </article>
          ))}
        </div>
      </Card>
    </div>
  )
}
