import { useEffect, useState } from 'react'

import { getDisplayConfig, updateDisplayConfig } from '../api/display'
import type { DisplayConfigUpdateRequest } from '../api/types'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { StatusNotice } from '../components/StatusNotice'
import { useAsyncData } from '../hooks/useAsyncData'
import { toTitleCase } from '../utils/format'

export function DisplaySettingsPage() {
  const { data, loading, error, reload, setData } = useAsyncData(getDisplayConfig, [])
  const [draft, setDraft] = useState<DisplayConfigUpdateRequest | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

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
      setSaveError(null)
      setSaved(false)
      const updated = await updateDisplayConfig(draft)
      setData(updated)
      setDraft(updated)
      setSaved(true)
    } catch (caught) {
      setSaveError(caught instanceof Error ? caught.message : 'Unable to save display config.')
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        title="Display settings"
        description="Controls for the fullscreen slideshow surface. These values shape how /display behaves on the device."
        actions={
          <div className="button-row">
            <button type="button" className="button button--ghost" onClick={() => void reload()}>
              Reload
            </button>
            <a href="/display" className="button button--ghost">
              Open display
            </a>
          </div>
        }
      />

      {loading ? <StatusNotice variant="loading" title="Loading display settings…" /> : null}
      {error ? <StatusNotice variant="error" title="Could not load display settings" detail={error} /> : null}
      {saveError ? <StatusNotice variant="error" title="Could not save display settings" detail={saveError} /> : null}
      {saved ? <StatusNotice variant="success" title="Display settings saved" /> : null}

      {draft ? (
        <div className="two-column-grid">
          <Card title="Slideshow behavior" eyebrow="/display config">
            <form className="form-grid" onSubmit={(event) => void handleSubmit(event)}>
              <label>
                <span>Dwell time (seconds)</span>
                <input
                  type="number"
                  min={5}
                  step={1}
                  value={draft.interval_seconds}
                  onChange={(event) =>
                    setDraft((current) =>
                      current
                        ? {
                            ...current,
                            interval_seconds: Number(event.target.value),
                          }
                        : current,
                    )
                  }
                />
              </label>
              <label>
                <span>Transition duration (ms)</span>
                <input
                  type="number"
                  min={200}
                  step={100}
                  value={draft.transition_duration_ms}
                  onChange={(event) =>
                    setDraft((current) =>
                      current
                        ? {
                            ...current,
                            transition_duration_ms: Number(event.target.value),
                          }
                        : current,
                    )
                  }
                />
              </label>
              <label>
                <span>Fit mode</span>
                <select
                  value={draft.fit_mode}
                  onChange={(event) =>
                    setDraft((current) =>
                      current
                        ? {
                            ...current,
                            fit_mode: event.target.value as DisplayConfigUpdateRequest['fit_mode'],
                          }
                        : current,
                    )
                  }
                >
                  <option value="contain">Contain</option>
                  <option value="cover">Cover</option>
                </select>
              </label>
              <label>
                <span>Playback mode</span>
                <select
                  value={draft.playback_mode}
                  onChange={(event) =>
                    setDraft((current) =>
                      current
                        ? {
                            ...current,
                            playback_mode: event.target.value as DisplayConfigUpdateRequest['playback_mode'],
                          }
                        : current,
                    )
                  }
                >
                  <option value="sequential">Sequential</option>
                  <option value="shuffle">Shuffle</option>
                </select>
              </label>
              <label>
                <span>Refresh playlist every (seconds)</span>
                <input
                  type="number"
                  min={15}
                  step={15}
                  value={draft.refresh_interval_seconds}
                  onChange={(event) =>
                    setDraft((current) =>
                      current
                        ? {
                            ...current,
                            refresh_interval_seconds: Number(event.target.value),
                          }
                        : current,
                    )
                  }
                />
              </label>
              <label>
                <span>Transition mode</span>
                <input
                  type="text"
                  value={draft.transition_mode}
                  onChange={(event) =>
                    setDraft((current) =>
                      current
                        ? {
                            ...current,
                            transition_mode: event.target.value,
                          }
                        : current,
                    )
                  }
                />
              </label>
              <label className="field-span-full">
                <span>Idle message</span>
                <textarea
                  rows={4}
                  value={draft.idle_message}
                  onChange={(event) =>
                    setDraft((current) =>
                      current
                        ? {
                            ...current,
                            idle_message: event.target.value,
                          }
                        : current,
                    )
                  }
                />
              </label>
              <div className="form-actions">
                <button type="submit" className="button">
                  Save display settings
                </button>
              </div>
            </form>
          </Card>

          <Card title="What this changes" eyebrow="Behavior summary">
            <dl className="detail-list">
              <div>
                <dt>Playback mode</dt>
                <dd>{toTitleCase(draft.playback_mode)}</dd>
              </div>
              <div>
                <dt>Fit</dt>
                <dd>{toTitleCase(draft.fit_mode)}</dd>
              </div>
              <div>
                <dt>Transition</dt>
                <dd>{toTitleCase(draft.transition_mode)}</dd>
              </div>
              <div>
                <dt>Refresh cadence</dt>
                <dd>{draft.refresh_interval_seconds} seconds</dd>
              </div>
            </dl>
            <p className="card-muted">
              The display renderer keeps two image layers mounted so the next frame is decoded before the slide begins.
            </p>
          </Card>
        </div>
      ) : null}
    </div>
  )
}
