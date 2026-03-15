import { useEffect, useState } from 'react'

import { getSettings, updateSettings } from '../api/settings'
import type { FrameSettings } from '../api/types'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { StatusNotice } from '../components/StatusNotice'
import { useAsyncData } from '../hooks/useAsyncData'

export function SettingsPage() {
  const { data, loading, error, reload, setData } = useAsyncData(getSettings, [])
  const [draft, setDraft] = useState<FrameSettings | null>(null)
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [saveError, setSaveError] = useState<string | null>(null)

  useEffect(() => {
    if (data) {
      setDraft(data)
    }
  }, [data])

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!draft) {
      return
    }

    try {
      setSaveState('saving')
      setSaveError(null)
      const updated = await updateSettings(draft)
      setData(updated)
      setDraft(updated)
      setSaveState('saved')
    } catch (caught) {
      setSaveState('error')
      setSaveError(caught instanceof Error ? caught.message : 'Unable to save settings.')
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        title="Settings"
        description="Device settings used for future imports, generated derivatives, and the frame identity shown in the admin UI."
        actions={
          <button type="button" className="button button--ghost" onClick={() => void reload()}>
            Reload
          </button>
        }
      />

      {loading ? <StatusNotice variant="loading" title="Loading settings…" /> : null}
      {error ? <StatusNotice variant="error" title="Could not load settings" detail={error} /> : null}

      {draft ? (
        <div className="two-column-grid">
          <Card title="Device defaults" eyebrow="Frame settings">
            <form className="form-grid" onSubmit={(event) => void handleSubmit(event)}>
              <label>
                <span>Frame name</span>
                <input
                  type="text"
                  value={draft.frame_name}
                  onChange={(event) =>
                    setDraft((current) =>
                      current
                        ? {
                            ...current,
                            frame_name: event.target.value,
                          }
                        : current,
                    )
                  }
                />
              </label>

              <label>
                <span>Display derivative width (px)</span>
                <input
                  type="number"
                  min={320}
                  step={10}
                  value={draft.display_variant_width}
                  onChange={(event) =>
                    setDraft((current) =>
                      current
                        ? {
                            ...current,
                            display_variant_width: Number(event.target.value),
                          }
                        : current,
                    )
                  }
                />
              </label>

              <label>
                <span>Display derivative height (px)</span>
                <input
                  type="number"
                  min={240}
                  step={10}
                  value={draft.display_variant_height}
                  onChange={(event) =>
                    setDraft((current) =>
                      current
                        ? {
                            ...current,
                            display_variant_height: Number(event.target.value),
                          }
                        : current,
                    )
                  }
                />
              </label>

              <label>
                <span>Thumbnail size (px)</span>
                <input
                  type="number"
                  min={64}
                  step={8}
                  value={draft.thumbnail_max_size}
                  onChange={(event) =>
                    setDraft((current) =>
                      current
                        ? {
                            ...current,
                            thumbnail_max_size: Number(event.target.value),
                          }
                        : current,
                    )
                  }
                />
              </label>

              <div className="form-actions">
                <button type="submit" className="button" disabled={saveState === 'saving'}>
                  {saveState === 'saving' ? 'Saving…' : 'Save settings'}
                </button>
              </div>
            </form>

            {saveState === 'saved' ? (
              <StatusNotice variant="success" title="Settings saved" detail="Future imports will use the updated derivative sizes." />
            ) : null}
            {saveState === 'error' ? (
              <StatusNotice variant="error" title="Could not save settings" detail={saveError ?? undefined} />
            ) : null}
          </Card>

          <Card title="Stored playback defaults" eyebrow="Also available on /display-settings">
            <dl className="detail-list">
              <div>
                <dt>Dwell time</dt>
                <dd>{draft.slideshow_interval_seconds} seconds</dd>
              </div>
              <div>
                <dt>Transition</dt>
                <dd>{draft.transition_mode}</dd>
              </div>
              <div>
                <dt>Duration</dt>
                <dd>{draft.transition_duration_ms} ms</dd>
              </div>
              <div>
                <dt>Fit mode</dt>
                <dd>{draft.fit_mode}</dd>
              </div>
              <div>
                <dt>Shuffle</dt>
                <dd>{draft.shuffle_enabled ? 'Enabled' : 'Disabled'}</dd>
              </div>
            </dl>
            <p className="card-muted">
              Playback behavior is surfaced separately so the admin UI can keep device sizing and slideshow tuning easy to find.
            </p>
            <a href="/display-settings" className="button button--ghost">
              Open display settings
            </a>
          </Card>
        </div>
      ) : null}
    </div>
  )
}
