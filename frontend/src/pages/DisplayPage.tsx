import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import { useLocation } from 'react-router-dom'

import { getDefaultDisplayConfig, getDisplayPlaylist } from '../api/display'
import type { DisplayConfig, DisplayPlaylist, PlaylistItem, SleepSchedule } from '../api/types'
import { BootScreen, type BootScreenDemoFrame, type BootScreenMessage, useBootScreenDemo } from '../components/BootScreen'

type LayerStage = 'hidden' | 'prepped' | 'visible' | 'incoming' | 'outgoing'

interface DisplayLayer {
  item: PlaylistItem | null
  stage: LayerStage
}

const INITIAL_LAYERS: DisplayLayer[] = [
  { item: null, stage: 'hidden' },
  { item: null, stage: 'hidden' },
]

const EMPTY_PLAYLIST: DisplayPlaylist = {
  collection_id: null,
  collection_name: null,
  shuffle_enabled: false,
  playlist_revision: 'empty',
  profile: getDefaultDisplayConfig(),
  items: [],
  sleep_schedule: null,
}

const INITIAL_BOOT_MESSAGE: BootScreenMessage = {
  kicker: 'SPF5000',
  title: 'Preparing display',
  detail: 'Starting the fullscreen slideshow runtime.',
  secondary: 'Fetching display settings and the current playlist.',
  tone: 'booting',
  animateDots: true,
}

export function DisplayPage() {
  const location = useLocation()
  const [config, setConfig] = useState<DisplayConfig>(getDefaultDisplayConfig())
  const [playlist, setPlaylist] = useState<DisplayPlaylist>(EMPTY_PLAYLIST)
  const [layers, setLayers] = useState<DisplayLayer[]>(INITIAL_LAYERS)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSleeping, setIsSleeping] = useState(false)
  const [bootMessage, setBootMessage] = useState<BootScreenMessage>(INITIAL_BOOT_MESSAGE)

  const configRef = useRef(config)
  const playlistRef = useRef(playlist)
  const layersRef = useRef(layers)
  const activeLayerRef = useRef(0)
  const currentIndexRef = useRef(0)
  const startedRef = useRef(false)
  const transitionRef = useRef(false)
  const advanceTimerRef = useRef<number | null>(null)
  const finalizeTimerRef = useRef<number | null>(null)
  const isSleepingRef = useRef(false)
  const demoFrames = useMemo<BootScreenDemoFrame[]>(
    () => [
      {
        title: 'Preparing display',
        detail: 'Starting the SPF5000 fullscreen runtime.',
        secondary: 'Mounting display services and waking the slideshow shell.',
        tone: 'booting',
        animateDots: true,
        durationMs: 1800,
      },
      {
        title: 'Checking schedule',
        detail: 'Comparing quiet hours against the frame’s local clock.',
        secondary: 'Quiet hours 23:00 → 07:00 are configured but inactive right now.',
        tone: 'booting',
        animateDots: true,
        durationMs: 1800,
      },
      {
        title: 'Loading media',
        detail: 'Preloading display-sized photos for a clean handoff.',
        secondary: 'Decoding the first slide before anything moves on screen.',
        tone: 'booting',
        animateDots: true,
        durationMs: 2200,
      },
      {
        title: 'Ready',
        detail: 'Demo mode is holding on the boot screen.',
        secondary: 'Remove ?demo=boot from the URL to return to live display playback.',
        tone: 'empty',
        durationMs: 2600,
      },
    ],
    [],
  )
  const showBootDemo = useMemo(() => new URLSearchParams(location.search).get('demo') === 'boot', [location.search])
  const demoMessage = useBootScreenDemo(showBootDemo, demoFrames)

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

  const transitionToItem = useCallback(async (nextIndex: number) => {
    const items = playlistRef.current.items
    const nextItem = items[nextIndex]
    if (!nextItem || transitionRef.current) {
      return
    }

    try {
      await preloadImage(nextItem.display_url)
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

      scheduleAdvance(configRef.current.slideshow_interval_seconds * 1000)
    }, configRef.current.transition_duration_ms + 80)
  }, [])

  const scheduleAdvance = useCallback(
    (delayMs: number) => {
      clearTimers()
      if (isSleepingRef.current) {
        return
      }
      advanceTimerRef.current = window.setTimeout(() => {
        void advanceToNext()
      }, Math.max(delayMs, 1000))
    },
    [clearTimers],
  )

  const advanceToNext = useCallback(async () => {
    const items = playlistRef.current.items
    if (items.length <= 1) {
      scheduleAdvance(configRef.current.slideshow_interval_seconds * 1000)
      return
    }

    const nextIndex = selectNextIndex(currentIndexRef.current, items.length)
    await transitionToItem(nextIndex)
  }, [scheduleAdvance, transitionToItem])

  const bootPlaylist = useCallback(
    async (nextPlaylist: DisplayPlaylist, nextConfig: DisplayConfig) => {
      const firstItem = nextPlaylist.items[0]
      if (!firstItem) {
        startedRef.current = false
        transitionRef.current = false
        clearTimers()
        setLayers(INITIAL_LAYERS)
        setError(null)
        setLoading(false)
        setBootMessage({
          kicker: 'SPF5000',
          title: 'No photos ready yet',
          detail: nextConfig.idle_message,
          secondary: nextPlaylist.collection_name
            ? `Selected collection: ${nextPlaylist.collection_name}.`
            : 'Add photos from the admin UI to build the first playlist.',
          tone: 'empty',
        })
        return
      }

      try {
        setBootMessage({
          kicker: 'SPF5000',
          title: 'Loading media',
          detail: `Preloading “${firstItem.filename}” for the first transition-free frame.`,
          secondary: nextPlaylist.collection_name
            ? `Collection: ${nextPlaylist.collection_name}.`
            : 'Preparing the default collection.',
          tone: 'booting',
          animateDots: true,
        })
        await preloadImage(firstItem.display_url)
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
        setBootMessage({
          kicker: 'SPF5000',
          title: 'Ready',
          detail: `Loaded ${nextPlaylist.items.length} photo${nextPlaylist.items.length === 1 ? '' : 's'} for playback.`,
          secondary: 'Starting the slideshow now.',
          tone: 'empty',
        })
        scheduleAdvance(nextConfig.slideshow_interval_seconds * 1000)
      } catch (caught) {
        const detail = caught instanceof Error ? caught.message : 'Unable to prepare slideshow.'
        setLoading(false)
        setError(detail)
        setBootMessage({
          kicker: 'SPF5000',
          title: 'Display unavailable',
          detail,
          secondary: 'The display will try again on the next playlist refresh.',
          tone: 'error',
        })
      }
    },
    [clearTimers, scheduleAdvance],
  )

  const updateSleepState = useCallback(
    (schedule: SleepSchedule | null) => {
      const nowSleeping = schedule ? isInSleepWindow(schedule) : false
      const wasSleeping = isSleepingRef.current
      isSleepingRef.current = nowSleeping
      setIsSleeping(nowSleeping)

      if (wasSleeping && !nowSleeping) {
        if (startedRef.current) {
          scheduleAdvance(configRef.current.slideshow_interval_seconds * 1000)
        } else if (playlistRef.current.items.length > 0) {
          void bootPlaylist(playlistRef.current, configRef.current)
        }
      } else if (!wasSleeping && nowSleeping) {
        clearTimers()
        transitionRef.current = false
        setLayers((current) =>
          current.map((layer, index) => {
            if (index === activeLayerRef.current) {
              return { ...layer, stage: 'visible' }
            }

            return { ...layer, stage: 'hidden' }
          }),
        )
      }

      return nowSleeping
    },
    [bootPlaylist, clearTimers, scheduleAdvance],
  )

  const syncDisplayData = useCallback(
    async (initial = false) => {
      try {
        if (initial) {
          setLoading(true)
          setBootMessage({
            kicker: 'SPF5000',
            title: 'Preparing display',
            detail: 'Fetching display settings and the current playlist.',
            secondary: 'The slideshow runtime is starting up on this screen.',
            tone: 'booting',
            animateDots: true,
          })
        }

        const nextPlaylist = await getDisplayPlaylist()
        const nextConfig = nextPlaylist.profile
        configRef.current = nextConfig
        playlistRef.current = nextPlaylist
        setConfig(nextConfig)
        setPlaylist(nextPlaylist)
        setBootMessage({
          kicker: 'SPF5000',
          title: 'Checking schedule',
          detail: 'Comparing quiet hours against the frame’s local device time.',
          secondary: describeSleepSchedule(nextPlaylist.sleep_schedule),
          tone: 'booting',
          animateDots: true,
        })
        updateSleepState(nextPlaylist.sleep_schedule)

        const currentItemId = layersRef.current[activeLayerRef.current]?.item?.asset_id
        const currentIndex = currentItemId ? nextPlaylist.items.findIndex((item) => item.asset_id === currentItemId) : -1

        if (!startedRef.current || currentIndex === -1) {
          await bootPlaylist(nextPlaylist, nextConfig)
          return
        }

        currentIndexRef.current = currentIndex
        setError(null)
        setLoading(false)
        scheduleAdvance(nextConfig.slideshow_interval_seconds * 1000)
      } catch (caught) {
        setLoading(false)
        if (!startedRef.current) {
          const detail = caught instanceof Error ? caught.message : 'Unable to load display data.'
          setError(detail)
          setBootMessage({
            kicker: 'SPF5000',
            title: 'Display unavailable',
            detail,
            secondary: 'Check the backend and playlist source, then refresh the display.',
            tone: 'error',
          })
        }
      }
    },
    [bootPlaylist, scheduleAdvance, updateSleepState],
  )

  useEffect(() => {
    document.body.classList.add('display-body')
    void syncDisplayData(true)

    return () => {
      document.body.classList.remove('display-body')
      clearTimers()
    }
  }, [clearTimers, syncDisplayData])

  // Evaluate sleep schedule using the kiosk browser's local device time so the
  // display can enter and leave sleep mode without waiting for a playlist refresh.
  useEffect(() => {
    const checkSleep = () => {
      updateSleepState(playlistRef.current.sleep_schedule)
    }

    checkSleep()
    const timer = window.setInterval(checkSleep, 1_000)
    return () => window.clearInterval(timer)
  }, [updateSleepState])

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

  const idleMessage = useMemo(() => {
    if (demoMessage) {
      return demoMessage
    }

    if (error && !showIdle) {
      return {
        kicker: 'SPF5000',
        title: 'Display unavailable',
        detail: error,
        secondary: 'Check the backend and playlist source, then refresh the display.',
        tone: 'error' as const,
      }
    }

    if (!loading && showIdle && !error) {
      return {
        kicker: 'SPF5000',
        title: bootMessage.title,
        detail: bootMessage.detail ?? config.idle_message,
        secondary: bootMessage.secondary,
        tone: bootMessage.tone ?? 'empty',
        animateDots: bootMessage.animateDots,
      }
    }

    return bootMessage
  }, [bootMessage, config.idle_message, demoMessage, error, loading, showIdle])

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
                <img src={layer.item.display_url} alt={layer.item.filename} draggable={false} />
              </figure>
            ) : null}
          </div>
        ))}

        {(showIdle || demoMessage || (error && !layers.some((layer) => layer.item))) && !isSleeping ? <BootScreen message={idleMessage} /> : null}

        {isSleeping ? <div className="display-sleep-overlay" aria-hidden="true" /> : null}
      </div>
    </main>
  )
}

function selectNextIndex(currentIndex: number, length: number): number {
  if (length <= 1) {
    return 0
  }

  return (currentIndex + 1) % length
}

/**
 * Returns true when the current device-local browser time falls inside the
 * configured sleep window. The start time is inclusive and the end time is
 * exclusive, so a schedule ending at 08:00 wakes at 08:00.
 */
function isInSleepWindow(schedule: SleepSchedule): boolean {
  if (!schedule.sleep_schedule_enabled) {
    return false
  }

  const now = new Date()
  const currentMinutes = now.getHours() * 60 + now.getMinutes()

  const [startH = 0, startM = 0] = schedule.sleep_start_local_time.split(':').map(Number)
  const [endH = 0, endM = 0] = schedule.sleep_end_local_time.split(':').map(Number)
  const startMinutes = startH * 60 + startM
  const endMinutes = endH * 60 + endM

  if (startMinutes === endMinutes) {
    // Identical times — treat as disabled (backend rejects this when enabled,
    // but guard here for safety)
    return false
  }

  if (startMinutes < endMinutes) {
    // Same-day window e.g. 09:00 → 17:00
    return currentMinutes >= startMinutes && currentMinutes < endMinutes
  }

  // Overnight window e.g. 22:00 → 06:00
  return currentMinutes >= startMinutes || currentMinutes < endMinutes
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

function describeSleepSchedule(schedule: SleepSchedule | null): string {
  if (!schedule?.sleep_schedule_enabled) {
    return 'No quiet hours are active for this frame.'
  }

  return `Quiet hours ${schedule.sleep_start_local_time} → ${schedule.sleep_end_local_time} are configured on this frame.`
}
