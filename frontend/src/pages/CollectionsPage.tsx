import { useEffect, useMemo, useState } from 'react'

import { createCollection, getCollections, updateCollection } from '../api/collections'
import type { CollectionSummary, CollectionUpsertRequest } from '../api/types'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { StatusNotice } from '../components/StatusNotice'
import { useAsyncData } from '../hooks/useAsyncData'
import { formatDateTime, formatNumber } from '../utils/format'

type DraftMap = Record<string, CollectionUpsertRequest>

const emptyDraft: CollectionUpsertRequest = {
  name: '',
  description: '',
  is_active: true,
}

export function CollectionsPage() {
  const { data, loading, error, reload, setData } = useAsyncData(getCollections, [])
  const [newCollection, setNewCollection] = useState<CollectionUpsertRequest>(emptyDraft)
  const [drafts, setDrafts] = useState<DraftMap>({})
  const [feedback, setFeedback] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)

  useEffect(() => {
    if (!data) {
      return
    }

    setDrafts(
      Object.fromEntries(
        data.map((collection) => [
          collection.id,
          {
            name: collection.name,
            description: collection.description ?? '',
            is_active: collection.is_active,
          },
        ]),
      ),
    )
  }, [data])

  const activeCount = useMemo(
    () => (data ?? []).filter((collection) => collection.is_active).length,
    [data],
  )

  async function handleCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!newCollection.name.trim()) {
      return
    }

    try {
      setSaveError(null)
      const created = await createCollection({
        ...newCollection,
        name: newCollection.name.trim(),
      })
      setData((current) => (current ? [created, ...current] : [created]))
      setNewCollection(emptyDraft)
      setFeedback(`Created ${created.name}.`)
    } catch (caught) {
      setSaveError(caught instanceof Error ? caught.message : 'Could not create collection.')
    }
  }

  async function handleSave(collection: CollectionSummary) {
    const draft = drafts[collection.id]
    if (!draft) {
      return
    }

    try {
      setSaveError(null)
      const updated = await updateCollection(collection.id, {
        ...draft,
        name: draft.name.trim(),
      })
      setData((current) =>
        current ? current.map((item) => (item.id === updated.id ? updated : item)) : current,
      )
      setFeedback(`Saved ${updated.name}.`)
    } catch (caught) {
      setSaveError(caught instanceof Error ? caught.message : 'Could not update collection.')
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        title="Collections"
        description="Create logical display groups and adjust the ones already available to the playlist builder."
        actions={
          <button type="button" className="button button--ghost" onClick={() => void reload()}>
            Refresh
          </button>
        }
      />

      {feedback ? <StatusNotice variant="success" title={feedback} /> : null}
      {saveError ? <StatusNotice variant="error" title="Collection update failed" detail={saveError} /> : null}

      <div className="two-column-grid">
        <Card title="Create collection" eyebrow="New group">
          <form className="form-grid" onSubmit={(event) => void handleCreate(event)}>
            <label>
              <span>Name</span>
              <input
                type="text"
                value={newCollection.name}
                onChange={(event) =>
                  setNewCollection((current) => ({
                    ...current,
                    name: event.target.value,
                  }))
                }
              />
            </label>
            <label>
              <span>Description</span>
              <textarea
                rows={4}
                value={newCollection.description}
                onChange={(event) =>
                  setNewCollection((current) => ({
                    ...current,
                    description: event.target.value,
                  }))
                }
              />
            </label>
            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={newCollection.is_active}
                onChange={(event) =>
                  setNewCollection((current) => ({
                    ...current,
                    is_active: event.target.checked,
                  }))
                }
              />
              <span>Available for playback</span>
            </label>
            <div className="form-actions">
              <button type="submit" className="button">
                Add collection
              </button>
            </div>
          </form>
        </Card>

        <Card title="Overview" eyebrow="At a glance">
          <dl className="detail-list">
            <div>
              <dt>Total collections</dt>
              <dd>{formatNumber(data?.length)}</dd>
            </div>
            <div>
              <dt>Active collections</dt>
              <dd>{formatNumber(activeCount)}</dd>
            </div>
          </dl>
          <p className="card-muted">
            Collections let the backend define playlist membership without cluttering the display route.
          </p>
        </Card>
      </div>

      {loading ? <StatusNotice variant="loading" title="Loading collections…" /> : null}
      {error ? <StatusNotice variant="error" title="Could not load collections" detail={error} /> : null}

      <div className="card-grid">
        {(data ?? []).map((collection) => {
          const draft = drafts[collection.id] ?? emptyDraft
          return (
            <Card key={collection.id} title={collection.name} eyebrow="Collection">
              <form
                className="form-grid"
                onSubmit={(event) => {
                  event.preventDefault()
                  void handleSave(collection)
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
                        [collection.id]: {
                          ...draft,
                          name: event.target.value,
                        },
                      }))
                    }
                  />
                </label>
                <label>
                  <span>Description</span>
                  <textarea
                    rows={3}
                    value={draft.description ?? ''}
                    onChange={(event) =>
                      setDrafts((current) => ({
                        ...current,
                        [collection.id]: {
                          ...draft,
                          description: event.target.value,
                        },
                      }))
                    }
                  />
                </label>
                <label className="checkbox-field">
                  <input
                    type="checkbox"
                    checked={draft.is_active}
                    onChange={(event) =>
                      setDrafts((current) => ({
                        ...current,
                        [collection.id]: {
                          ...draft,
                          is_active: event.target.checked,
                        },
                      }))
                    }
                  />
                  <span>Collection is active</span>
                </label>
                <dl className="detail-list detail-list--compact">
                  <div>
                    <dt>Assets</dt>
                    <dd>{formatNumber(collection.asset_count)}</dd>
                  </div>
                  <div>
                    <dt>Updated</dt>
                    <dd>{formatDateTime(collection.updated_at)}</dd>
                  </div>
                </dl>
                <div className="form-actions">
                  <button type="submit" className="button">
                    Save collection
                  </button>
                </div>
              </form>
            </Card>
          )
        })}
      </div>

      {!loading && !error && (data?.length ?? 0) === 0 ? (
        <StatusNotice
          variant="empty"
          title="No collections configured"
          detail="Create one above so imported assets can be grouped for playback."
        />
      ) : null}
    </div>
  )
}
