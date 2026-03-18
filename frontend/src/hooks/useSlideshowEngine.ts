import { useCallback, useMemo, useRef, useState, type CSSProperties } from 'react'
import { buildBackgroundStyle, getDefaultDisplayConfig } from '../api/display'
import type {
  BackgroundFillMode,
  DisplayConfig,
  DisplayPlaylist,
  DisplayTransitionMode,
  PlaylistItem,
} from '../api/types'

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

interface DisplayBackgroundPresentation {
  resolvedMode: ResolvedBackgroundFillMode
  style: CSSProperties
}

type ResolvedBackgroundFillMode = Exclude<BackgroundFillMode, 'adaptive_auto'>

const SHUFFLE_BAG_RECENT_LIMIT = 4

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

interface BootPlaylistResult {
  idleMessage: {
    kicker: string
    title: string
    detail: string
    secondary?: string
    tone: 'booting' | 'empty' | 'error'
    animateDots?: boolean
  }
  loading: false
  error: null
}

interface SlideshowCallbacks {
  onBootMessage: (msg: BootPlaylistResult['idleMessage']) => void
}

export function useSlideshowEngine(callbacks: SlideshowCallbacks) {
  const [playlist, setPlaylist] = useState<DisplayPlaylist>(EMPTY_PLAYLIST)
  const [layers, setLayers] = useState<DisplayLayer[]>(INITIAL_LAYERS)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const configRef = useRef<DisplayConfig>(getDefaultDisplayConfig())
  const playlistRef = useRef<DisplayPlaylist>(EMPTY_PLAYLIST)
  const layersRef = useRef<DisplayLayer[]>(INITIAL_LAYERS)
  const activeLayerRef = useRef(0)
  const currentIndexRef = useRef(0)
  const startedRef = useRef(false)
  const transitionRef = useRef(false)
  const advanceTimerRef = useRef<number | null>(null)
  const finalizeTimerRef = useRef<number | null>(null)
  const shuffleBagRef = useRef<string[]>([])
  const recentShuffleAssetIdsRef = useRef<string[]>([])

  const resetShuffleBagState = useCallback(() => {
    shuffleBagRef.current = []
    recentShuffleAssetIdsRef.current = []
  }, [])

  const rememberShownAsset = useCallback((assetId: string | null) => {
    if (!assetId) return
    recentShuffleAssetIdsRef.current = [...recentShuffleAssetIdsRef.current, assetId].slice(-SHUFFLE_BAG_RECENT_LIMIT)
  }, [])

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

  const transitionStyleVars = useMemo(
    () => getTransitionStyleVars(configRef.current.transition_mode),
    [],
  )
  const transitionDurationMs = useMemo(
    () => getTransitionDurationMs(configRef.current),
    [],
  )

  const transitionToItem = useCallback(
    async (nextIndex: number) => {
      const items = playlistRef.current.items
      const nextItem = items[nextIndex]
      if (!nextItem || transitionRef.current) return

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
          if (index === incomingLayerIndex) return { item: nextItem, stage: 'prepped' }
          if (index === currentLayerIndex) return { ...layer, stage: 'visible' }
          return layer
        }),
      )

      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => {
          setLayers((current) =>
            current.map((layer, index) => {
              if (index === incomingLayerIndex) return { ...layer, stage: 'incoming' }
              if (index === currentLayerIndex) return { ...layer, stage: 'outgoing' }
              return layer
            }),
          )
        })
      })

      finalizeTimerRef.current = window.setTimeout(() => {
        activeLayerRef.current = incomingLayerIndex
        currentIndexRef.current = nextIndex
        transitionRef.current = false
        rememberShownAsset(nextItem.asset_id)

        setLayers((current) =>
          current.map((layer, index) => {
            if (index === incomingLayerIndex) return { ...layer, stage: 'visible' }
            return { ...layer, stage: 'hidden' }
          }),
        )

        scheduleAdvance(configRef.current.slideshow_interval_seconds * 1000)
      }, finalizeDelayMs)
    },
    [rememberShownAsset],
  )

  const takeNextShuffleBagIndex = useCallback((items: PlaylistItem[]): number => {
    if (items.length <= 1) return 0

    const validIds = new Set(items.map((item) => item.asset_id))
    const currentItemId = layersRef.current[activeLayerRef.current]?.item?.asset_id ?? null
    const existingQueue = shuffleBagRef.current.filter((assetId) => validIds.has(assetId) && assetId !== currentItemId)

    if (existingQueue.length > 0) {
      shuffleBagRef.current = existingQueue
    } else {
      shuffleBagRef.current = buildShuffleBagAssetIds(
        items,
        recentShuffleAssetIdsRef.current,
        currentItemId ? [currentItemId] : [],
      )
    }

    const nextId = shuffleBagRef.current.shift()
    if (!nextId) return 0
    const nextIndex = items.findIndex((item) => item.asset_id === nextId)
    return nextIndex >= 0 ? nextIndex : 0
  }, [])

  const scheduleAdvance = useCallback(
    (delayMs: number) => {
      clearTimers()
      if (isSleepingRef.current || isFullscreenAlertActiveRef.current) return
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
    const nextIndex = usesShuffleBag(configRef.current)
      ? takeNextShuffleBagIndex(items)
      : selectNextIndex(currentIndexRef.current, items.length)
    await transitionToItem(nextIndex)
  }, [scheduleAdvance, takeNextShuffleBagIndex, transitionToItem])

  const isSleepingRef = useRef(false)
  const isFullscreenAlertActiveRef = useRef(false)

  const bootPlaylist = useCallback(
    async (nextPlaylist: DisplayPlaylist, nextConfig: DisplayConfig) => {
      if (usesShuffleBag(nextConfig)) {
        resetShuffleBagState()
      }

      const firstIndex = usesShuffleBag(nextConfig) ? takeNextShuffleBagIndex(nextPlaylist.items) : 0
      const firstItem = nextPlaylist.items[firstIndex]

      if (!firstItem) {
        startedRef.current = false
        transitionRef.current = false
        clearTimers()
        resetShuffleBagState()
        setLayers(INITIAL_LAYERS)
        setError(null)
        setLoading(false)
        callbacks.onBootMessage({
          kicker: 'SPF5000',
          title: nextPlaylist.collection_name ? 'No images in this collection' : 'No images found',
          detail: nextConfig.idle_message,
          secondary: nextPlaylist.collection_name
            ? `Selected collection: ${nextPlaylist.collection_name}.`
            : 'Add photos from the admin UI to build the first playlist.',
          tone: 'empty',
        })
        return
      }

      try {
        callbacks.onBootMessage({
          kicker: 'SPF5000',
          title: 'Loading media',
          detail: `Preloading "${firstItem.filename}" for the first transition-free frame.`,
          secondary: nextPlaylist.collection_name
            ? `Collection: ${nextPlaylist.collection_name}.`
            : 'Preparing the default collection.',
          tone: 'booting',
          animateDots: true,
        })
        await preloadImage(firstItem.display_url)
        activeLayerRef.current = 0
        currentIndexRef.current = firstIndex
        startedRef.current = true
        transitionRef.current = false
        rememberShownAsset(firstItem.asset_id)
        setLayers([
          { item: firstItem, stage: 'visible' },
          { item: null, stage: 'hidden' },
        ])
        setLoading(false)
        setError(null)
        callbacks.onBootMessage({
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
        callbacks.onBootMessage({
          kicker: 'SPF5000',
          title: 'Display unavailable',
          detail,
          secondary: 'The display will try again on the next playlist refresh.',
          tone: 'error',
        })
      }
    },
    [callbacks, clearTimers, rememberShownAsset, resetShuffleBagState, scheduleAdvance, takeNextShuffleBagIndex],
  )

  return {
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
    advanceTimerRef,
    finalizeTimerRef,
    isSleepingRef,
    isFullscreenAlertActiveRef,
    clearTimers,
    resetShuffleBagState,
    scheduleAdvance,
    advanceToNext,
    bootPlaylist,
    transitionStyleVars,
    transitionDurationMs,
  }
}

function selectNextIndex(currentIndex: number, length: number): number {
  if (length <= 1) return 0
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

function getTransitionFinalizeDelayMs(config: Pick<DisplayConfig, 'transition_duration_ms' | 'transition_mode'>): number {
  const durationMs = getTransitionDurationMs(config)
  return durationMs > 0 ? durationMs + 80 : 40
}

function usesShuffleBag(config: Pick<DisplayConfig, 'shuffle_enabled' | 'shuffle_bag_enabled'>): boolean {
  return config.shuffle_enabled && config.shuffle_bag_enabled
}

function buildShuffleBagAssetIds(items: PlaylistItem[], recentAssetIds: string[], additionalBlockedIds: string[] = []): string[] {
  const assetIds = items.map((item) => item.asset_id)
  if (assetIds.length <= 1) return assetIds

  const blockedCount = Math.min(SHUFFLE_BAG_RECENT_LIMIT, Math.max(assetIds.length - 1, 0))
  const validIds = new Set(assetIds)
  const blockedIds = [
    ...recentAssetIds.filter((assetId) => validIds.has(assetId)),
    ...additionalBlockedIds.filter((assetId) => validIds.has(assetId)),
  ].slice(-blockedCount)
  const shuffled = shuffleAssetIds(assetIds)

  if (blockedIds.length === 0) return shuffled

  const blockedSet = new Set(blockedIds)
  const safe = shuffled.filter((assetId) => !blockedSet.has(assetId))
  const delayed = shuffled.filter((assetId) => blockedSet.has(assetId))
  return [...safe, ...delayed]
}

function shuffleAssetIds(assetIds: string[]): string[] {
  const shuffled = [...assetIds]
  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1))
    ;[shuffled[index], shuffled[swapIndex]] = [shuffled[swapIndex], shuffled[index]]
  }
  return shuffled
}

export function getDisplayBackgroundPresentation(
  mode: BackgroundFillMode,
  item: PlaylistItem | null,
  viewportAspectRatio: number,
): DisplayBackgroundPresentation {
  const resolvedMode = resolveBackgroundFillMode(mode, item, viewportAspectRatio)
  const background = item?.background
  const palette = getBackgroundPalette(background)
  const dominant = background?.dominant_color ?? palette[0] ?? '#000'

  return {
    resolvedMode,
    style: {
      background: buildBackgroundStyle(resolvedMode, background),
      ['--display-bg-image' as string]: item?.display_url ? `url("${item.display_url}")` : 'none',
      ['--display-bg-dominant' as string]: dominant,
      ['--display-bg-color-1' as string]: palette[0] ?? dominant,
      ['--display-bg-color-2' as string]: palette[1] ?? dominant,
      ['--display-bg-color-3' as string]: palette[2] ?? dominant,
    },
  }
}

function resolveBackgroundFillMode(
  mode: BackgroundFillMode,
  item: PlaylistItem | null,
  viewportAspectRatio: number,
): ResolvedBackgroundFillMode {
  if (mode !== 'adaptive_auto') return mode

  const background = item?.background
  if (!background?.ready) return 'black'

  const imageAspectRatio = getImageAspectRatio(item)
  const mismatch = Math.max(imageAspectRatio / viewportAspectRatio, viewportAspectRatio / imageAspectRatio)
  const paletteSize = background.gradient_colors?.filter((color) => color.length > 0).length ?? 0

  if (mismatch >= 1.55) return 'blurred_backdrop'
  if (mismatch >= 1.28) return 'mirrored_edges'
  if (paletteSize >= 2) return 'palette_wash'
  if (background.dominant_color) return 'soft_vignette'
  return paletteSize > 0 ? 'gradient' : 'black'
}

function getImageAspectRatio(item: PlaylistItem | null): number {
  if (!item || item.width <= 0 || item.height <= 0) return 16 / 9
  return item.width / item.height
}

function getBackgroundPalette(itemBackground: PlaylistItem['background'] | undefined): string[] {
  const colors = itemBackground?.gradient_colors?.filter((color) => color.length > 0) ?? []
  const dominant = itemBackground?.dominant_color ?? null

  if (colors.length >= 3) return colors.slice(0, 3)
  if (colors.length === 2 && dominant) return [colors[0], colors[1], dominant]
  if (colors.length === 1 && dominant) return [colors[0], dominant, dominant]
  if (dominant) return [dominant, dominant, dominant]
  if (colors.length === 2) return [colors[0], colors[1], colors[1]]
  if (colors.length === 1) return [colors[0], colors[0], colors[0]]
  return ['#000', '#000', '#000']
}
