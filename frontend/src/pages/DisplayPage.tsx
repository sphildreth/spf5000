import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import { useLocation } from 'react-router-dom'

import { getDefaultDisplayConfig, getDisplayPlaylist } from '../api/display'
import { getDisplayAlerts, getDisplayWeather } from '../api/weather'
import type {
  BackgroundFillMode,
  DisplayConfig,
  DisplayPlaylist,
  DisplayTransitionMode,
  PlaylistItem,
} from '../api/types'
import { BootScreen, type BootScreenDemoFrame, type BootScreenMessage, useBootScreenDemo } from '../components/BootScreen'
import { WeatherAlertOverlay } from '../components/WeatherAlertOverlay'
import { WeatherWidget } from '../components/WeatherWidget'
import { useSleepManager, describeSleepSchedule } from '../hooks/useSleepManager'
import { getDisplayBackgroundPresentation, useSlideshowEngine } from '../hooks/useSlideshowEngine'
import { useWeatherOverlay } from '../hooks/useWeatherOverlay'

type LayerStage = 'hidden' | 'prepped' | 'visible' | 'incoming' | 'outgoing'
type ResolvedBackgroundFillMode = Exclude<BackgroundFillMode, 'adaptive_auto'>

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
  const [bootMessage, setBootMessage] = useState<BootScreenMessage>(INITIAL_BOOT_MESSAGE)
  const [viewportAspectRatio, setViewportAspectRatio] = useState(() => getViewportAspectRatio())
  const [isFullscreenAlertActive, setIsFullscreenAlertActive] = useState(false)
  const fullscreenAlertTimerRef = useRef<number | null>(null)
  const nextFullscreenRepeatAtRef = useRef<number | null>(null)
  const activeRepeatAlertIdRef = useRef<string | null>(null)
  const slideshowCallbacks = useMemo(() => ({ onBootMessage: setBootMessage }), [])

  const {
    playlist,
    playlistRef,
    layers,
    layersRef,
    loading,
    error,
    setPlaylist,
    setLoading,
    setError,
    configRef,
    activeLayerRef,
    currentIndexRef,
    startedRef,
    transitionRef,
    clearTimers,
    scheduleAdvance,
    bootPlaylist,
  } = useSlideshowEngine(slideshowCallbacks)
  const {
    weather,
    alerts,
    setWeather,
    setAlerts,
    syncDisplayOverlays,
    EMPTY_DISPLAY_WEATHER,
    EMPTY_DISPLAY_ALERTS,
  } = useWeatherOverlay()

  const onWakeRef = useRef<(() => void) | null>(null)
  const onSleepRef = useRef<(() => void) | null>(null)

  onWakeRef.current = () => {
    if (startedRef.current) {
      scheduleAdvance(configRef.current.slideshow_interval_seconds * 1000)
    } else if (playlistRef.current.items.length > 0) {
      void bootPlaylist(playlistRef.current, configRef.current)
    }
  }

  onSleepRef.current = () => {
    clearTimers()
    transitionRef.current = false
  }

  const handleWake = useCallback(() => {
    onWakeRef.current?.()
  }, [])

  const handleSleep = useCallback(() => {
    onSleepRef.current?.()
  }, [])

  const { isSleeping, updateSleepState } = useSleepManager({
    onWake: handleWake,
    onSleep: handleSleep,
  })

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
        detail: 'Comparing quiet hours against the configured display timezone.',
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

  useEffect(() => {
    configRef.current = config
  }, [config, configRef])

  const showBootDemo = useMemo(() => new URLSearchParams(location.search).get('demo') === 'boot', [location.search])
  const demoMessage = useBootScreenDemo(showBootDemo, demoFrames)
  const transitionStyleVars = useMemo(() => getTransitionStyleVars(config.transition_mode), [config.transition_mode])
  const transitionDurationMs = useMemo(
    () => getTransitionDurationMs(config),
    [config.transition_duration_ms, config.transition_mode],
  )

  useEffect(() => {
    const handleResize = () => {
      setViewportAspectRatio(getViewportAspectRatio())
    }

    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const clearAlertTimers = useCallback(() => {
    if (fullscreenAlertTimerRef.current !== null) {
      window.clearTimeout(fullscreenAlertTimerRef.current)
      fullscreenAlertTimerRef.current = null
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
        setPlaylist(nextPlaylist)
        setConfig(nextConfig)
        setWeather(nextWeather)
        setAlerts(nextAlerts)
        setBootMessage({
          kicker: 'SPF5000',
          title: 'Checking schedule',
          detail: 'Comparing quiet hours against the configured display timezone.',
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
    [
      EMPTY_DISPLAY_ALERTS,
      EMPTY_DISPLAY_WEATHER,
      activeLayerRef,
      bootPlaylist,
      configRef,
      currentIndexRef,
      layersRef,
      playlistRef,
      scheduleAdvance,
      setAlerts,
      setError,
      setLoading,
      setPlaylist,
      setWeather,
      startedRef,
      updateSleepState,
    ],
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
  }, [clearAlertTimers, clearTimers, setError, setLoading, showBootDemo, syncDisplayData])

  useEffect(() => {
    if (showBootDemo) return

    const checkSleep = () => {
      updateSleepState(playlistRef.current.sleep_schedule)
    }

    checkSleep()
    const timer = window.setInterval(checkSleep, 1_000)
    return () => window.clearInterval(timer)
  }, [showBootDemo, updateSleepState, playlistRef])

  useEffect(() => {
    if (showBootDemo) return

    const intervalMs = Math.max(config.refresh_interval_seconds, 15) * 1000
    const timer = window.setInterval(() => {
      void syncDisplayData(false)
    }, intervalMs)

    return () => {
      window.clearInterval(timer)
    }
  }, [config.refresh_interval_seconds, showBootDemo, syncDisplayData])

  useEffect(() => {
    if (showBootDemo) return

    const timer = window.setInterval(() => {
      void syncDisplayOverlays()
    }, OVERLAY_REFRESH_SECONDS * 1000)

    return () => {
      window.clearInterval(timer)
    }
  }, [showBootDemo, syncDisplayOverlays])

  useEffect(() => {
    if (showBootDemo) return

    if (isSleeping) {
      clearAlertTimers()
      setIsFullscreenAlertActive(false)
      return
    }

    const dominant = alerts.dominant_alert
    const mode = alerts.presentation.mode

    if (!dominant || (mode !== 'fullscreen' && mode !== 'fullscreen_repeat')) {
      activeRepeatAlertIdRef.current = null
      nextFullscreenRepeatAtRef.current = null
      clearAlertTimers()
      setIsFullscreenAlertActive(false)
      return
    }

    if (mode === 'fullscreen') {
      activeRepeatAlertIdRef.current = dominant.id
      nextFullscreenRepeatAtRef.current = null
      clearAlertTimers()
      setIsFullscreenAlertActive(true)
      return
    }

    if (activeRepeatAlertIdRef.current !== dominant.id) {
      activeRepeatAlertIdRef.current = dominant.id
      nextFullscreenRepeatAtRef.current = null
    }

    if (isFullscreenAlertActive) {
      return
    }

    const now = Date.now()
    if (nextFullscreenRepeatAtRef.current && now < nextFullscreenRepeatAtRef.current) {
      return
    }

    nextFullscreenRepeatAtRef.current = now + alerts.presentation.repeat_interval_minutes * 60 * 1000
    setIsFullscreenAlertActive(true)
    clearAlertTimers()
    fullscreenAlertTimerRef.current = window.setTimeout(() => {
      setIsFullscreenAlertActive(false)
    }, Math.max(alerts.presentation.repeat_display_seconds, 5) * 1000)
  }, [alerts, clearAlertTimers, isSleeping, showBootDemo, isFullscreenAlertActive])

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
    if (demoMessage) return demoMessage

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
          <DisplayBackgroundLayer
            key={`bg-${index}`}
            layer={layer}
            mode={config.background_fill_mode}
            viewportAspectRatio={viewportAspectRatio}
          />
        ))}

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

function DisplayBackgroundLayer({
  layer,
  mode,
  viewportAspectRatio,
}: {
  layer: DisplayLayer
  mode: BackgroundFillMode
  viewportAspectRatio: number
}) {
  const presentation = getDisplayBackgroundPresentation(mode, layer.item, viewportAspectRatio)
  const usesBackdropImage =
    presentation.resolvedMode === 'blurred_backdrop' ||
    presentation.resolvedMode === 'mirrored_edges' ||
    presentation.resolvedMode === 'soft_vignette'
  const usesMirroredEdges = presentation.resolvedMode === 'mirrored_edges'
  const usesPaletteWash = presentation.resolvedMode === 'palette_wash'
  const showsVignette =
    presentation.resolvedMode === 'soft_vignette' ||
    presentation.resolvedMode === 'palette_wash' ||
    presentation.resolvedMode === 'blurred_backdrop' ||
    presentation.resolvedMode === 'mirrored_edges'

  return (
    <div
      className={`display-bg-layer display-bg-layer--${layer.stage} display-bg-layer--mode-${presentation.resolvedMode}`}
      style={presentation.style}
      aria-hidden="true"
    >
      {usesBackdropImage ? <div className="display-bg-image display-bg-image--backdrop" /> : null}
      {usesMirroredEdges ? (
        <>
          <div className="display-bg-mirror display-bg-mirror--left" />
          <div className="display-bg-mirror display-bg-mirror--right" />
          <div className="display-bg-image display-bg-image--center" />
        </>
      ) : null}
      {usesPaletteWash ? <div className="display-bg-overlay display-bg-overlay--wash" /> : null}
      {showsVignette ? <div className="display-bg-overlay display-bg-overlay--vignette" /> : null}
      {(presentation.resolvedMode === 'blurred_backdrop' || presentation.resolvedMode === 'mirrored_edges') && (
        <div className="display-bg-overlay display-bg-overlay--tint" />
      )}
      {presentation.resolvedMode === 'soft_vignette' ? <div className="display-bg-overlay display-bg-overlay--soft-glow" /> : null}
    </div>
  )
}

function getViewportAspectRatio(): number {
  if (typeof window === 'undefined' || window.innerWidth <= 0 || window.innerHeight <= 0) {
    return 16 / 9
  }
  return window.innerWidth / window.innerHeight
}

function getTransitionStyleVars(mode: DisplayTransitionMode): TransitionStyleVars {
  switch (mode) {
    case 'slide-right-to-left':
      return {
        hiddenX: '-100%', hiddenY: '0%', hiddenOpacity: '1',
        preppedX: '100%', preppedY: '0%', preppedOpacity: '1',
        outgoingX: '-100%', outgoingY: '0%', outgoingOpacity: '1',
      }
    case 'slide-top-to-bottom':
      return {
        hiddenX: '0%', hiddenY: '100%', hiddenOpacity: '1',
        preppedX: '0%', preppedY: '-100%', preppedOpacity: '1',
        outgoingX: '0%', outgoingY: '100%', outgoingOpacity: '1',
      }
    case 'slide-bottom-to-top':
      return {
        hiddenX: '0%', hiddenY: '-100%', hiddenOpacity: '1',
        preppedX: '0%', preppedY: '100%', preppedOpacity: '1',
        outgoingX: '0%', outgoingY: '-100%', outgoingOpacity: '1',
      }
    case 'cut':
      return {
        hiddenX: '0%', hiddenY: '0%', hiddenOpacity: '0',
        preppedX: '0%', preppedY: '0%', preppedOpacity: '0',
        outgoingX: '0%', outgoingY: '0%', outgoingOpacity: '0',
      }
    case 'slide':
    default:
      return {
        hiddenX: '100%', hiddenY: '0%', hiddenOpacity: '1',
        preppedX: '-100%', preppedY: '0%', preppedOpacity: '1',
        outgoingX: '100%', outgoingY: '0%', outgoingOpacity: '1',
      }
  }
}

function getTransitionDurationMs(config: Pick<DisplayConfig, 'transition_duration_ms' | 'transition_mode'>): number {
  return config.transition_mode === 'cut' ? 0 : Math.max(config.transition_duration_ms, 0)
}
