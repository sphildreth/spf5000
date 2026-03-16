import { useEffect, useMemo, useState } from 'react'

import { getCollections } from '../api/collections'
import { getDisplayConfig, updateDisplayConfig } from '../api/display'
import { getSleepSchedule, updateSleepSchedule } from '../api/settings'
import {
  asDisplayTransitionMode,
  DISPLAY_TRANSITION_MODE_OPTIONS,
  getDisplayTransitionModeLabel,
  type DisplayConfig,
  type DisplayConfigUpdateRequest,
  type SleepSchedule,
  type SleepScheduleUpdateRequest,
} from '../api/types'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { StatusNotice } from '../components/StatusNotice'
import { useAsyncData } from '../hooks/useAsyncData'
import { toTitleCase } from '../utils/format'

interface DisplaySettingsData {
  config: DisplayConfig
  collections: Awaited<ReturnType<typeof getCollections>>
  sleepSchedule: SleepSchedule
}

export function DisplaySettingsPage() {
  const { data, loading, error, reload, setData } = useAsyncData<DisplaySettingsData>(
    async () => {
      const [config, collections, sleepSchedule] = await Promise.all([getDisplayConfig(), getCollections(), getSleepSchedule()])
      return { config, collections, sleepSchedule }
    },
    [],
  )
  const [draft, setDraft] = useState<DisplayConfig | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const [sleepDraft, setSleepDraft] = useState<SleepSchedule | null>(null)
  const [sleepSaveError, setSleepSaveError] = useState<string | null>(null)
  const [sleepSaved, setSleepSaved] = useState(false)

  useEffect(() => {
    if (data) {
      setDraft(data.config)
      setSleepDraft(data.sleepSchedule)
    }
  }, [data])

  const selectedCollectionName = useMemo(() => {
    if (!draft?.selected_collection_id) {
      return 'All active photos'
    }

    return (
      data?.collections.find((collection) => collection.id === draft.selected_collection_id)?.name ??
      draft.selected_collection_id
    )
  }, [data, draft])

  async function handleSleepSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!sleepDraft) {
      return
    }

    if (sleepDraft.sleep_schedule_enabled && sleepDraft.sleep_start_local_time === sleepDraft.sleep_end_local_time) {
      setSleepSaveError('Start time and end time must differ when the sleep schedule is enabled.')
      return
    }

    try {
      setSleepSaveError(null)
      setSleepSaved(false)
      const request: SleepScheduleUpdateRequest = {
        sleep_schedule_enabled: sleepDraft.sleep_schedule_enabled,
        sleep_start_local_time: sleepDraft.sleep_start_local_time,
        sleep_end_local_time: sleepDraft.sleep_end_local_time,
      }
      const updated = await updateSleepSchedule(request)
      setData((current) => (current ? { ...current, sleepSchedule: updated } : current))
      setSleepDraft(updated)
      setSleepSaved(true)
    } catch (caught) {
      setSleepSaveError(caught instanceof Error ? caught.message : 'Unable to save sleep schedule.')
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!draft) {
      return
    }

    try {
      setSaveError(null)
      setSaved(false)
      const request: DisplayConfigUpdateRequest = {
        name: draft.name.trim(),
        selected_collection_id: draft.selected_collection_id,
        slideshow_interval_seconds: draft.slideshow_interval_seconds,
        transition_mode: draft.transition_mode,
        transition_duration_ms: draft.transition_duration_ms,
        fit_mode: draft.fit_mode,
        shuffle_enabled: draft.shuffle_enabled,
        idle_message: draft.idle_message,
        refresh_interval_seconds: draft.refresh_interval_seconds,
      }
      const updated = await updateDisplayConfig(request)
      setData((current) => (current ? { ...current, config: updated } : current))
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
      {sleepSaveError ? <StatusNotice variant="error" title="Could not save sleep schedule" detail={sleepSaveError} /> : null}
      {sleepSaved ? <StatusNotice variant="success" title="Sleep schedule saved" /> : null}

      {draft ? (
        <div className="two-column-grid">
          <Card title="Slideshow behavior" eyebrow="/display config">
            <form className="form-grid" onSubmit={(event) => void handleSubmit(event)}>
              <label>
                <span>Profile name</span>
                <input
                  type="text"
                  value={draft.name}
                  onChange={(event) =>
                    setDraft((current) =>
                      current
                        ? {
                            ...current,
                            name: event.target.value,
                          }
                        : current,
                    )
                  }
                />
              </label>
              <label>
                <span>Selected collection</span>
                <select
                  value={draft.selected_collection_id ?? ''}
                  onChange={(event) =>
                    setDraft((current) =>
                      current
                        ? {
                            ...current,
                            selected_collection_id: event.target.value || null,
                          }
                        : current,
                    )
                  }
                >
                  <option value="">All active photos</option>
                  {(data?.collections ?? []).map((collection) => (
                    <option key={collection.id} value={collection.id}>
                      {collection.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Dwell time (seconds)</span>
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
                <span>Transition duration (ms)</span>
                <input
                  type="number"
                  min={100}
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
                            fit_mode: event.target.value as DisplayConfig['fit_mode'],
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
                <span>Transition mode</span>
                <select
                  value={draft.transition_mode}
                  onChange={(event) =>
                    setDraft((current) =>
                      current
                        ? {
                            ...current,
                            transition_mode: asDisplayTransitionMode(event.target.value, current.transition_mode),
                          }
                        : current,
                    )
                  }
                >
                  {DISPLAY_TRANSITION_MODE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
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
                <dd>{draft.shuffle_enabled ? 'Shuffle' : 'Sequential'}</dd>
              </div>
              <div>
                <dt>Collection</dt>
                <dd>{selectedCollectionName}</dd>
              </div>
              <div>
                <dt>Fit</dt>
                <dd>{toTitleCase(draft.fit_mode)}</dd>
              </div>
              <div>
                <dt>Transition</dt>
                <dd>{getDisplayTransitionModeLabel(draft.transition_mode)}</dd>
              </div>
              <div>
                <dt>Playlist refresh</dt>
                <dd>{draft.refresh_interval_seconds} seconds</dd>
              </div>
            </dl>
            <p className="card-muted">
              The display renderer keeps two image layers mounted so the next frame is decoded before the slide begins.
            </p>
          </Card>

          {sleepDraft ? (
            <Card title="Sleep schedule" eyebrow="Display power">
              <form className="form-grid" onSubmit={(event) => void handleSleepSubmit(event)}>
                <label className="checkbox-field">
                  <input
                    type="checkbox"
                    checked={sleepDraft.sleep_schedule_enabled}
                    onChange={(event) =>
                      setSleepDraft((current) => (current ? { ...current, sleep_schedule_enabled: event.target.checked } : current))
                    }
                  />
                  <span>Enable sleep schedule</span>
                </label>
                <label>
                  <span>Sleep start (local time)</span>
                  <input
                    type="time"
                    value={sleepDraft.sleep_start_local_time}
                    onChange={(event) =>
                      setSleepDraft((current) => (current ? { ...current, sleep_start_local_time: event.target.value } : current))
                    }
                  />
                </label>
                <label>
                  <span>Sleep end (local time)</span>
                  <input
                    type="time"
                    value={sleepDraft.sleep_end_local_time}
                    onChange={(event) =>
                      setSleepDraft((current) => (current ? { ...current, sleep_end_local_time: event.target.value } : current))
                    }
                  />
                </label>
                <p className="card-muted">
                  SPF5000 compares these times against the frame&apos;s local device time on the display hardware. Overnight
                  windows (for example 22:00 → 06:00) are supported, and the frame wakes at the configured end time.
                </p>
                <div className="form-actions">
                  <button type="submit" className="button">
                    Save sleep schedule
                  </button>
                </div>
              </form>
            </Card>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
