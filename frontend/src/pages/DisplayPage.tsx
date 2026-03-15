import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'

import { getDefaultDisplayConfig, getDisplayConfig, getDisplayPlaylist } from '../api/display'
import type { DisplayConfig, DisplayPlaylist, PlaylistItem } from '../api/types'

type LayerStage = 'hidden' | 'prepped' | 'visible' | 'incoming' | 'outgoing'

interface DisplayLayer {
  item: PlaylistItem | null
  stage: LayerStage
}

const INITIAL_LAYERS: DisplayLayer[] = [
  { item: null, stage: 'hidden' },
  { item: null, stage: 'hidden' },
]

export function DisplayPage() {
  const [config, setConfig] = useState<DisplayConfig>(getDefaultDisplayConfig())
  const [playlist, setPlaylist] = useState<DisplayPlaylist>({ items: [] })
  const [layers, setLayers] = useState<DisplayLayer[]>(INITIAL_LAYERS)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const configRef = useRef(config)
  const playlistRef = useRef(playlist)
  const layersRef = useRef(layers)
  const activeLayerRef = useRef(0)
  const currentIndexRef = useRef(0)
  const startedRef = useRef(false)
  const transitionRef = useRef(false)
  const advanceTimerRef = useRef<number | null>(null)
  const finalizeTimerRef = useRef<number | null>(null)

  useEffect(() => {
    configRef.current = config
  }, [config])

  useEffect(() => {
    playlistRef.current = playlist
  }, [playlist])

  useEffect(() => {
    layersRef.current = layers
  }, [layers])

  const clearTimers = useCallback(() => {
    if (advanceTimerRef.current !== null) {
      window.clearTimeout(advanceTimerRef.current)
      advanceTimerRef.current = null
    }

    if (finalizeTimerRef.current !== null) {
      window.clearTimeout(finalizeTimerRef.current)
      finalizeTimerRef.current = null
    }
  }, [])

  const transitionToItem = useCallback(
    async (nextIndex: number) => {
      const items = playlistRef.current.items
      const nextItem = items[nextIndex]
      if (!nextItem || transitionRef.current) {
        return
      }

      try {
        await preloadImage(nextItem.image_url)
      } catch {
        scheduleAdvance(5000)
        return
      }

      const currentLayerIndex = activeLayerRef.current
      const incomingLayerIndex = currentLayerIndex === 0 ? 1 : 0
      transitionRef.current = true

      setLayers((current) =>
        current.map((layer, index) => {
          if (index === incomingLayerIndex) {
            return { item: nextItem, stage: 'prepped' }
          }

          if (index === currentLayerIndex) {
            return { ...layer, stage: 'visible' }
          }

          return layer
        }),
      )

      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => {
          setLayers((current) =>
            current.map((layer, index) => {
              if (index === incomingLayerIndex) {
                return { ...layer, stage: 'incoming' }
              }

              if (index === currentLayerIndex) {
                return { ...layer, stage: 'outgoing' }
              }

              return layer
            }),
          )
        })
      })

      finalizeTimerRef.current = window.setTimeout(() => {
        activeLayerRef.current = incomingLayerIndex
        currentIndexRef.current = nextIndex
        transitionRef.current = false

        setLayers((current) =>
          current.map((layer, index) => {
            if (index === incomingLayerIndex) {
              return { ...layer, stage: 'visible' }
            }

            return { ...layer, stage: 'hidden' }
          }),
        )

        scheduleAdvance(configRef.current.interval_seconds * 1000)
      }, configRef.current.transition_duration_ms + 80)
    },
    [],
  )

  const scheduleAdvance = useCallback(
    (delayMs: number) => {
      clearTimers()
      advanceTimerRef.current = window.setTimeout(() => {
        void advanceToNext()
      }, Math.max(delayMs, 1000))
    },
    [clearTimers],
  )

  const advanceToNext = useCallback(async () => {
    const items = playlistRef.current.items
    if (items.length <= 1) {
      scheduleAdvance(configRef.current.interval_seconds * 1000)
      return
    }

    const nextIndex = selectNextIndex(
      currentIndexRef.current,
      items.length,
      playlistRef.current.playback_mode ?? configRef.current.playback_mode,
    )

    await transitionToItem(nextIndex)
  }, [scheduleAdvance, transitionToItem])

  const bootPlaylist = useCallback(
    async (nextPlaylist: DisplayPlaylist) => {
      const firstItem = nextPlaylist.items[0]
      if (!firstItem) {
        startedRef.current = false
        transitionRef.current = false
        clearTimers()
        setLayers(INITIAL_LAYERS)
        setLoading(false)
        return
      }

      try {
        await preloadImage(firstItem.image_url)
        activeLayerRef.current = 0
        currentIndexRef.current = 0
        startedRef.current = true
        transitionRef.current = false
        setLayers([
          { item: firstItem, stage: 'visible' },
          { item: null, stage: 'hidden' },
        ])
        setLoading(false)
        setError(null)
        scheduleAdvance(configRef.current.interval_seconds * 1000)
      } catch (caught) {
        setLoading(false)
        setError(caught instanceof Error ? caught.message : 'Unable to prepare slideshow.')
      }
    },
    [clearTimers, scheduleAdvance],
  )

  const syncDisplayData = useCallback(
    async (initial = false) => {
      try {
        if (initial) {
          setLoading(true)
        }

        const [nextConfig, nextPlaylist] = await Promise.all([getDisplayConfig(), getDisplayPlaylist()])
        setConfig(nextConfig)
        setPlaylist(nextPlaylist)

        const currentItemId = layersRef.current[activeLayerRef.current]?.item?.id
        const currentIndex = currentItemId
          ? nextPlaylist.items.findIndex((item) => item.id === currentItemId)
          : -1

        if (!startedRef.current || currentIndex === -1) {
          await bootPlaylist(nextPlaylist)
          return
        }

        currentIndexRef.current = currentIndex
        setError(null)
        setLoading(false)
      } catch (caught) {
        setLoading(false)
        if (!startedRef.current) {
          setError(caught instanceof Error ? caught.message : 'Unable to load display data.')
        }
      }
    },
    [bootPlaylist],
  )

  useEffect(() => {
    document.body.classList.add('display-body')
    void syncDisplayData(true)

    return () => {
      document.body.classList.remove('display-body')
      clearTimers()
    }
  }, [clearTimers, syncDisplayData])

  useEffect(() => {
    const intervalMs = Math.max(config.refresh_interval_seconds, 15) * 1000
    const timer = window.setInterval(() => {
      void syncDisplayData(false)
    }, intervalMs)

    return () => {
      window.clearInterval(timer)
    }
  }, [config.refresh_interval_seconds, syncDisplayData])

  const showIdle = playlist.items.length === 0 || !layers.some((layer) => layer.item)

  const idleTitle = useMemo(() => {
    if (loading) {
      return 'Preparing slideshow'
    }

    if (error) {
      return 'Display unavailable'
    }

    return 'No photos ready yet'
  }, [error, loading])

  const idleDetail = useMemo(() => {
    if (loading) {
      return 'The frame is fetching display settings and building the current playlist.'
    }

    if (error) {
      return error
    }

    return config.idle_message
  }, [config.idle_message, error, loading])

  return (
    <main className="display-page" style={{ ['--display-fit' as string]: config.fit_mode } as CSSProperties}>
      <div className="display-stage" aria-label="SPF5000 fullscreen slideshow">
        {layers.map((layer, index) => (
          <div
            key={index}
            className={`display-layer display-layer--${layer.stage}`}
            style={{ ['--transition-duration' as string]: `${config.transition_duration_ms}ms` } as CSSProperties}
          >
            {layer.item ? (
              <figure className="display-media">
                <img src={layer.item.image_url} alt={layer.item.title} draggable={false} />
              </figure>
            ) : null}
          </div>
        ))}

        {showIdle ? (
          <div className="display-idle-shell">
            <div className="display-idle-card">
              <p className="display-idle-kicker">SPF5000</p>
              <h1>{idleTitle}</h1>
              <p>{idleDetail}</p>
            </div>
          </div>
        ) : null}
      </div>
    </main>
  )
}

function selectNextIndex(currentIndex: number, length: number, playbackMode: DisplayConfig['playback_mode']): number {
  if (length <= 1) {
    return 0
  }

  if (playbackMode === 'shuffle') {
    let nextIndex = currentIndex
    while (nextIndex === currentIndex) {
      nextIndex = Math.floor(Math.random() * length)
    }
    return nextIndex
  }

  return (currentIndex + 1) % length
}

function preloadImage(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.decoding = 'async'
    image.onload = () => {
      const decodePromise = typeof image.decode === 'function' ? image.decode() : Promise.resolve()
      decodePromise.then(() => resolve()).catch(() => resolve())
    }
    image.onerror = () => reject(new Error(`Could not load image: ${src}`))
    image.src = src
  })
}
