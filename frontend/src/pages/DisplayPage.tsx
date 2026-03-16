import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import { useLocation } from 'react-router-dom'

import { getDefaultDisplayConfig, getDisplayPlaylist } from '../api/display'
import { getDisplayAlerts, getDisplayWeather } from '../api/weather'
import type {
  DisplayAlerts,
  DisplayConfig,
  DisplayPlaylist,
  DisplayTransitionMode,
  DisplayWeather,
  PlaylistItem,
  SleepSchedule,
} from '../api/types'
import { BootScreen, type BootScreenDemoFrame, type BootScreenMessage, useBootScreenDemo } from '../components/BootScreen'
import { WeatherAlertOverlay } from '../components/WeatherAlertOverlay'
import { WeatherWidget } from '../components/WeatherWidget'

type LayerStage = 'hidden' | 'prepped' | 'visible' | 'incoming' | 'outgoing'

interface DisplayLayer {
  item: PlaylistItem | null
  stage: LayerStage
}

interface TransitionStyleVars {
  hiddenX: string
  hiddenY: string
  hiddenOpacity: string
  preppedX: string
  preppedY: string
  preppedOpacity: string
  outgoingX: string
  outgoingY: string
  outgoingOpacity: string
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

const EMPTY_DISPLAY_WEATHER: DisplayWeather = {
  enabled: false,
  position: 'top-right',
  units: 'f',
  show_precipitation: true,
  show_humidity: true,
  show_wind: true,
  provider_status: {
    provider_name: 'nws',
    provider_display_name: 'National Weather Service',
    status: 'disabled',
    available: true,
    configured: false,
    location_label: '',
    last_weather_refresh_at: null,
    last_alert_refresh_at: null,
    last_successful_weather_refresh_at: null,
    last_successful_alert_refresh_at: null,
    current_error: null,
    updated_at: '',
  },
  current_conditions: null,
}

const EMPTY_DISPLAY_ALERTS: DisplayAlerts = {
  provider_status: {
    provider_name: 'nws',
    provider_display_name: 'National Weather Service',
    status: 'disabled',
    available: true,
    configured: false,
    location_label: '',
    last_weather_refresh_at: null,
    last_alert_refresh_at: null,
    last_successful_weather_refresh_at: null,
    last_successful_alert_refresh_at: null,
    current_error: null,
    updated_at: '',
  },
  dominant_alert: null,
  active_alerts: [],
  presentation: {
    mode: 'none',
    fallback_mode: null,
    repeat_interval_minutes: 5,
    repeat_display_seconds: 20,
    alert_count: 0,
  },
}

const INITIAL_BOOT_MESSAGE: BootScreenMessage = {
  kicker: 'SPF5000',
  title: 'Preparing display',
  detail: 'Starting the fullscreen slideshow runtime.',
  secondary: 'Fetching display settings and the current playlist.',
  tone: 'booting',
  animateDots: true,
}

const OVERLAY_REFRESH_SECONDS = 30

export function DisplayPage() {
  const location = useLocation()
  const [config, setConfig] = useState<DisplayConfig>(getDefaultDisplayConfig())
  const [playlist, setPlaylist] = useState<DisplayPlaylist>(EMPTY_PLAYLIST)
  const [weather, setWeather] = useState<DisplayWeather>(EMPTY_DISPLAY_WEATHER)
  const [alerts, setAlerts] = useState<DisplayAlerts>(EMPTY_DISPLAY_ALERTS)
  const [layers, setLayers] = useState<DisplayLayer[]>(INITIAL_LAYERS)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSleeping, setIsSleeping] = useState(false)
  const [isFullscreenAlertActive, setIsFullscreenAlertActive] = useState(false)
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
  const isFullscreenAlertActiveRef = useRef(false)
  const fullscreenAlertTimerRef = useRef<number | null>(null)
  const nextFullscreenRepeatAtRef = useRef<number | null>(null)
  const activeRepeatAlertIdRef = useRef<string | null>(null)

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

  // Allow `/display?demo=boot` to showcase the branded boot screen without
  // depending on live playlist timing or backend availability.
  const showBootDemo = useMemo(() => new URLSearchParams(location.search).get('demo') === 'boot', [location.search])
  const demoMessage = useBootScreenDemo(showBootDemo, demoFrames)
  const transitionStyleVars = useMemo(() => getTransitionStyleVars(config.transition_mode), [config.transition_mode])
  const transitionDurationMs = useMemo(
    () => getTransitionDurationMs(config),
    [config.transition_duration_ms, config.transition_mode],
  )

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

  const clearAlertTimers = useCallback(() => {
    if (fullscreenAlertTimerRef.current !== null) {
      window.clearTimeout(fullscreenAlertTimerRef.current)
      fullscreenAlertTimerRef.current = null
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
    const finalizeDelayMs = getTransitionFinalizeDelayMs(configRef.current)
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
    }, finalizeDelayMs)
  }, [])

  const scheduleAdvance = useCallback(
    (delayMs: number) => {
      clearTimers()
      if (isSleepingRef.current || isFullscreenAlertActiveRef.current) {
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

  const setFullscreenAlertActiveState = useCallback(
    (active: boolean) => {
      const wasActive = isFullscreenAlertActiveRef.current
      if (wasActive === active) {
        return
      }

      isFullscreenAlertActiveRef.current = active
      setIsFullscreenAlertActive(active)

      if (active) {
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
        return
      }

      if (isSleepingRef.current) {
        return
      }

      if (startedRef.current) {
        scheduleAdvance(configRef.current.slideshow_interval_seconds * 1000)
      } else if (playlistRef.current.items.length > 0) {
        void bootPlaylist(playlistRef.current, configRef.current)
      }
    },
    [bootPlaylist, clearTimers, scheduleAdvance],
  )

  const updateSleepState = useCallback(
    (schedule: SleepSchedule | null) => {
      const nowSleeping = schedule ? isInSleepWindow(schedule) : false
      const wasSleeping = isSleepingRef.current
      isSleepingRef.current = nowSleeping
      setIsSleeping(nowSleeping)

      if (wasSleeping && !nowSleeping) {
        if (isFullscreenAlertActiveRef.current) {
          return nowSleeping
        }
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

  const syncDisplayOverlays = useCallback(async () => {
    const [weatherResult, alertsResult] = await Promise.allSettled([getDisplayWeather(), getDisplayAlerts()])

    if (weatherResult.status === 'fulfilled') {
      setWeather(weatherResult.value)
    }

    if (alertsResult.status === 'fulfilled') {
      setAlerts(alertsResult.value)
    }
  }, [])

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

        const [playlistResult, weatherResult, alertsResult] = await Promise.allSettled([
          getDisplayPlaylist(),
          getDisplayWeather(),
          getDisplayAlerts(),
        ])

        if (playlistResult.status !== 'fulfilled') {
          throw playlistResult.reason
        }

        const nextPlaylist = playlistResult.value
        const nextWeather = weatherResult.status === 'fulfilled' ? weatherResult.value : EMPTY_DISPLAY_WEATHER
        const nextAlerts = alertsResult.status === 'fulfilled' ? alertsResult.value : EMPTY_DISPLAY_ALERTS
        const nextConfig = nextPlaylist.profile

        configRef.current = nextConfig
        playlistRef.current = nextPlaylist
        setConfig(nextConfig)
        setPlaylist(nextPlaylist)
        setWeather(nextWeather)
        setAlerts(nextAlerts)
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
    document.documentElement.style.cursor = 'none'
    document.body.style.cursor = 'none'
    if (showBootDemo) {
      clearTimers()
      clearAlertTimers()
      setLoading(false)
      setError(null)
      return () => {
        document.documentElement.style.removeProperty('cursor')
        document.body.style.removeProperty('cursor')
        document.body.classList.remove('display-body')
        clearTimers()
        clearAlertTimers()
      }
    }

    void syncDisplayData(true)

    return () => {
      document.documentElement.style.removeProperty('cursor')
      document.body.style.removeProperty('cursor')
      document.body.classList.remove('display-body')
      clearTimers()
      clearAlertTimers()
    }
  }, [clearAlertTimers, clearTimers, showBootDemo, syncDisplayData])

  // Evaluate sleep schedule using the kiosk browser's local device time so the
  // display can enter and leave sleep mode without waiting for a playlist refresh.
  useEffect(() => {
    if (showBootDemo) {
      return
    }

    const checkSleep = () => {
      updateSleepState(playlistRef.current.sleep_schedule)
    }

    checkSleep()
    const timer = window.setInterval(checkSleep, 1_000)
    return () => window.clearInterval(timer)
  }, [showBootDemo, updateSleepState])

  useEffect(() => {
    if (showBootDemo) {
      return
    }

    const intervalMs = Math.max(config.refresh_interval_seconds, 15) * 1000
    const timer = window.setInterval(() => {
      void syncDisplayData(false)
    }, intervalMs)

    return () => {
      window.clearInterval(timer)
    }
  }, [config.refresh_interval_seconds, showBootDemo, syncDisplayData])

  useEffect(() => {
    if (showBootDemo) {
      return
    }

    const timer = window.setInterval(() => {
      void syncDisplayOverlays()
    }, OVERLAY_REFRESH_SECONDS * 1000)

    return () => {
      window.clearInterval(timer)
    }
  }, [showBootDemo, syncDisplayOverlays])

  useEffect(() => {
    if (showBootDemo) {
      return
    }

    if (isSleeping) {
      clearAlertTimers()
      setFullscreenAlertActiveState(false)
      return
    }

    const dominant = alerts.dominant_alert
    const mode = alerts.presentation.mode

    if (!dominant || (mode !== 'fullscreen' && mode !== 'fullscreen_repeat')) {
      activeRepeatAlertIdRef.current = null
      nextFullscreenRepeatAtRef.current = null
      clearAlertTimers()
      setFullscreenAlertActiveState(false)
      return
    }

    if (mode === 'fullscreen') {
      activeRepeatAlertIdRef.current = dominant.id
      nextFullscreenRepeatAtRef.current = null
      clearAlertTimers()
      setFullscreenAlertActiveState(true)
      return
    }

    if (activeRepeatAlertIdRef.current !== dominant.id) {
      activeRepeatAlertIdRef.current = dominant.id
      nextFullscreenRepeatAtRef.current = null
    }

    if (isFullscreenAlertActiveRef.current) {
      return
    }

    const now = Date.now()
    if (nextFullscreenRepeatAtRef.current && now < nextFullscreenRepeatAtRef.current) {
      return
    }

    nextFullscreenRepeatAtRef.current = now + alerts.presentation.repeat_interval_minutes * 60 * 1000
    setFullscreenAlertActiveState(true)
    clearAlertTimers()
    fullscreenAlertTimerRef.current = window.setTimeout(() => {
      setFullscreenAlertActiveState(false)
    }, Math.max(alerts.presentation.repeat_display_seconds, 5) * 1000)
  }, [alerts, clearAlertTimers, isSleeping, setFullscreenAlertActiveState, showBootDemo])

  const showIdle = playlist.items.length === 0 || !layers.some((layer) => layer.item)
  const bootOverlayVisible = Boolean((showIdle || demoMessage || (error && !layers.some((layer) => layer.item))) && !isSleeping)
  const showNonFullscreenAlerts =
    !isSleeping &&
    !isFullscreenAlertActive &&
    !bootOverlayVisible &&
    (alerts.presentation.mode === 'badge' ||
      alerts.presentation.mode === 'banner' ||
      (alerts.presentation.mode === 'fullscreen_repeat' && alerts.presentation.fallback_mode === 'banner'))

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
    <main
      className="display-page"
      style={
        {
          ['--display-fit' as string]: config.fit_mode,
          ['--transition-duration' as string]: `${transitionDurationMs}ms`,
          ['--display-hidden-x' as string]: transitionStyleVars.hiddenX,
          ['--display-hidden-y' as string]: transitionStyleVars.hiddenY,
          ['--display-hidden-opacity' as string]: transitionStyleVars.hiddenOpacity,
          ['--display-prepped-x' as string]: transitionStyleVars.preppedX,
          ['--display-prepped-y' as string]: transitionStyleVars.preppedY,
          ['--display-prepped-opacity' as string]: transitionStyleVars.preppedOpacity,
          ['--display-outgoing-x' as string]: transitionStyleVars.outgoingX,
          ['--display-outgoing-y' as string]: transitionStyleVars.outgoingY,
          ['--display-outgoing-opacity' as string]: transitionStyleVars.outgoingOpacity,
        } as CSSProperties
      }
    >
      <div className="display-stage" aria-label="SPF5000 fullscreen slideshow">
        {layers.map((layer, index) => (
          <div key={index} className={`display-layer display-layer--${layer.stage}`}>
            {layer.item ? (
              <figure className="display-media">
                <img src={layer.item.display_url} alt={layer.item.filename} draggable={false} />
              </figure>
            ) : null}
          </div>
        ))}

        {!isSleeping && !isFullscreenAlertActive ? <WeatherWidget weather={weather} /> : null}
        {showNonFullscreenAlerts ? <WeatherAlertOverlay alerts={alerts} fullscreenActive={false} /> : null}

        {bootOverlayVisible ? <BootScreen message={idleMessage} /> : null}

        {!isSleeping && isFullscreenAlertActive ? <WeatherAlertOverlay alerts={alerts} fullscreenActive /> : null}
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

function getTransitionStyleVars(mode: DisplayTransitionMode): TransitionStyleVars {
  switch (mode) {
    case 'slide-right-to-left':
      return {
        hiddenX: '-100%',
        hiddenY: '0%',
        hiddenOpacity: '1',
        preppedX: '100%',
        preppedY: '0%',
        preppedOpacity: '1',
        outgoingX: '-100%',
        outgoingY: '0%',
        outgoingOpacity: '1',
      }
    case 'slide-top-to-bottom':
      return {
        hiddenX: '0%',
        hiddenY: '100%',
        hiddenOpacity: '1',
        preppedX: '0%',
        preppedY: '-100%',
        preppedOpacity: '1',
        outgoingX: '0%',
        outgoingY: '100%',
        outgoingOpacity: '1',
      }
    case 'slide-bottom-to-top':
      return {
        hiddenX: '0%',
        hiddenY: '-100%',
        hiddenOpacity: '1',
        preppedX: '0%',
        preppedY: '100%',
        preppedOpacity: '1',
        outgoingX: '0%',
        outgoingY: '-100%',
        outgoingOpacity: '1',
      }
    case 'cut':
      return {
        hiddenX: '0%',
        hiddenY: '0%',
        hiddenOpacity: '0',
        preppedX: '0%',
        preppedY: '0%',
        preppedOpacity: '0',
        outgoingX: '0%',
        outgoingY: '0%',
        outgoingOpacity: '0',
      }
    case 'slide':
    default:
      return {
        hiddenX: '100%',
        hiddenY: '0%',
        hiddenOpacity: '1',
        preppedX: '-100%',
        preppedY: '0%',
        preppedOpacity: '1',
        outgoingX: '100%',
        outgoingY: '0%',
        outgoingOpacity: '1',
      }
  }
}

function getTransitionDurationMs(config: Pick<DisplayConfig, 'transition_duration_ms' | 'transition_mode'>): number {
  return config.transition_mode === 'cut' ? 0 : Math.max(config.transition_duration_ms, 0)
}

function getTransitionFinalizeDelayMs(config: Pick<DisplayConfig, 'transition_duration_ms' | 'transition_mode'>): number {
  const durationMs = getTransitionDurationMs(config)
  return durationMs > 0 ? durationMs + 80 : 40
}

function describeSleepSchedule(schedule: SleepSchedule | null): string {
  if (!schedule?.sleep_schedule_enabled) {
    return 'No quiet hours are active for this frame.'
  }

  return `Quiet hours ${schedule.sleep_start_local_time} → ${schedule.sleep_end_local_time} are configured on this frame.`
}
