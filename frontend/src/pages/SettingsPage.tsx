import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { getSettings, updateSettings } from '../api/settings'
import type { FrameSettings } from '../api/types'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { StatusNotice } from '../components/StatusNotice'
import { HOME_CITY_ACCENT_STYLE_OPTIONS, useTheme } from '../context/ThemeContext'
import { useAsyncData } from '../hooks/useAsyncData'

export function SettingsPage() {
  const { data, loading, error, reload, setData } = useAsyncData(getSettings, [])
  const [draft, setDraft] = useState<FrameSettings | null>(null)
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [saveError, setSaveError] = useState<string | null>(null)

  const { themes, activeThemeId, homeCityAccentStyle, applyThemeSettings, refreshThemes } = useTheme()
  const [selectedThemeId, setSelectedThemeId] = useState<string>(activeThemeId)
  const [selectedAccentStyle, setSelectedAccentStyle] = useState<string>(homeCityAccentStyle)

  // Sync local selectors when context updates (e.g. initial load from API)
  useEffect(() => {
    setSelectedThemeId(activeThemeId)
  }, [activeThemeId])

  useEffect(() => {
    setSelectedAccentStyle(homeCityAccentStyle)
  }, [homeCityAccentStyle])

  useEffect(() => {
    if (data) {
      setDraft(data)
      setSelectedThemeId(data.theme_id)
      setSelectedAccentStyle(data.home_city_accent_style)
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
      const updated = await updateSettings({
        ...draft,
        theme_id: selectedThemeId,
        home_city_accent_style: selectedAccentStyle,
      })
      setData(updated)
      setDraft(updated)
      applyThemeSettings(updated.theme_id, updated.home_city_accent_style)
      await refreshThemes()
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
            <Link to="/admin/display-settings" className="button button--ghost">
              Open display settings
            </Link>
          </Card>
        </div>
      ) : null}

      {/* ── Theme section (always visible) ── */}
      <Card title="Appearance" eyebrow="Theme & accent">
        <form
          className="form-grid"
          onSubmit={(event) => void handleSubmit(event)}
        >
          <label>
            <span>Theme</span>
            <select
              value={selectedThemeId}
              onChange={(e) => setSelectedThemeId(e.target.value)}
            >
              {themes.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Home-city accent style</span>
            <select
              value={selectedAccentStyle}
              onChange={(e) => setSelectedAccentStyle(e.target.value)}
            >
              {HOME_CITY_ACCENT_STYLE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label} — {o.description}
                </option>
              ))}
            </select>
          </label>

          {/* Lightweight theme preview swatches */}
          <div>
            <span style={{ display: 'block', marginBottom: '0.6rem', fontSize: '0.85rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Preview
            </span>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {themes.map((t) => {
                const isActive = t.id === selectedThemeId
                return (
                  <button
                    key={t.id}
                    type="button"
                    title={`${t.label} – ${t.description}`}
                    onClick={() => setSelectedThemeId(t.id)}
                    style={{
                      width: '2.6rem',
                      height: '2.6rem',
                      borderRadius: '10px',
                      background: t.tokens.panel,
                      border: isActive
                        ? `2px solid ${t.tokens.accent}`
                        : `2px solid ${t.tokens.border}`,
                      cursor: 'pointer',
                      position: 'relative',
                      overflow: 'hidden',
                      flexShrink: 0,
                    }}
                  >
                    {/* Mini accent stripe */}
                    <span
                      style={{
                        position: 'absolute',
                        bottom: 0,
                        left: 0,
                        right: 0,
                        height: '6px',
                        background: t.tokens.accent,
                        opacity: 0.9,
                      }}
                    />
                  </button>
                )
              })}
            </div>
            {(() => {
              const active = themes.find((t) => t.id === selectedThemeId)
              return active ? (
                <p style={{ margin: '0.5rem 0 0', fontSize: '0.85rem', color: 'var(--muted)' }}>
                  <strong style={{ color: 'var(--text)' }}>{active.label}</strong> — {active.description}
                </p>
              ) : null
            })()}
          </div>

          <div className="form-actions">
            <button type="submit" className="button">
              Apply theme
            </button>
          </div>
        </form>
      </Card>
    </div>
  )
}
