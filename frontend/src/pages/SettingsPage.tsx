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
        description="Core frame defaults exposed through /api/settings. Keep this page small and practical."
        actions={
          <button type="button" className="button button--ghost" onClick={() => void reload()}>
            Reload
          </button>
        }
      />

      {loading ? <StatusNotice variant="loading" title="Loading settings…" /> : null}
      {error ? <StatusNotice variant="error" title="Could not load settings" detail={error} /> : null}

      {draft ? (
        <Card title="Playback defaults" eyebrow="Frame settings">
          <form className="form-grid" onSubmit={(event) => void handleSubmit(event)}>
            <label>
              <span>Slideshow interval (seconds)</span>
              <input
                type="number"
                min={5}
                step={1}
                value={draft.slideshow_interval_seconds}
                onChange={(event) =>
                  setDraft((current) =>
                    current
                      ? {
                          ...current,
                          slideshow_interval_seconds: Number(event.target.value),
                        }
                      : current,
                  )
                }
              />
            </label>

            <label>
              <span>Transition mode</span>
              <select
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
              >
                <option value="slide">Slide</option>
                <option value="fade">Fade</option>
              </select>
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
                          fit_mode: event.target.value as FrameSettings['fit_mode'],
                        }
                      : current,
                  )
                }
              >
                <option value="contain">Contain</option>
                <option value="cover">Cover</option>
              </select>
            </label>

            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={draft.shuffle_enabled}
                onChange={(event) =>
                  setDraft((current) =>
                    current
                      ? {
                          ...current,
                          shuffle_enabled: event.target.checked,
                        }
                      : current,
                  )
                }
              />
              <span>Shuffle playlist order</span>
            </label>

            <div className="form-actions">
              <button type="submit" className="button" disabled={saveState === 'saving'}>
                {saveState === 'saving' ? 'Saving…' : 'Save settings'}
              </button>
            </div>
          </form>

          {saveState === 'saved' ? (
            <StatusNotice variant="success" title="Settings saved" detail="The frame defaults have been updated." />
          ) : null}
          {saveState === 'error' ? (
            <StatusNotice variant="error" title="Could not save settings" detail={saveError ?? undefined} />
          ) : null}
        </Card>
      ) : null}
    </div>
  )
}
