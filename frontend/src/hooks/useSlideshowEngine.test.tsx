import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'

import { getDefaultDisplayConfig, reportPlaybackProgress } from '../api/display'
import type { DisplayConfig, DisplayPlaylist, PlaylistItem } from '../api/types'
import { useSlideshowEngine } from './useSlideshowEngine'

vi.mock('../api/display', async () => {
  const actual = await vi.importActual<typeof import('../api/display')>('../api/display')
  return { ...actual, reportPlaybackProgress: vi.fn() }
})

const ASSET_COUNT = 40
const INTERVAL_SECONDS = 30
// A slide commits after the transition finalize delay, then waits out the interval.
const SLIDE_STEP_MS = INTERVAL_SECONDS * 1000 + 5_000

const CONFIG: DisplayConfig = {
  ...getDefaultDisplayConfig(),
  slideshow_interval_seconds: INTERVAL_SECONDS,
  transition_duration_ms: 100,
}

const ASSET_IDS = Array.from({ length: ASSET_COUNT }, (_, index) => `asset-${index}`)

function toItem(assetId: string): PlaylistItem {
  return {
    asset_id: assetId,
    filename: `${assetId}.jpg`,
    display_url: `/api/assets/${assetId}/variants/display`,
    thumbnail_url: `/api/assets/${assetId}/variants/thumbnail`,
    width: 1920,
    height: 1080,
    checksum_sha256: `checksum-${assetId}`,
    mime_type: 'image/jpeg',
    background: null,
  }
}

/**
 * A stand-in for the backend-owned playback cycle (ADR 0024): the client only walks the served
 * order and reports what it showed.
 */
function createCycleServer() {
  let order = [...ASSET_IDS]
  let position = 0
  let rolls = 0

  return {
    rolls: () => rolls,
    orderSnapshot: () => [...order],
    orderAt: (index: number) => order[index],
    advanceTo: (index: number) => {
      position = index
    },
    playlist(): DisplayPlaylist {
      return {
        collection_id: 'collection',
        collection_name: 'Collection',
        shuffle_enabled: true,
        playlist_revision: `cycle-${rolls}:${order.join(',')}`,
        playback_mode: 'shuffle_bag',
        playback_cycle_id: `cycle-${rolls}`,
        playback_position: position,
        profile: CONFIG,
        items: order.map(toItem),
        sleep_schedule: null,
      }
    },
    report(assetId: string) {
      const index = order.indexOf(assetId)
      if (index >= position) position = index + 1
    },
    /** Mirrors the backend rolling to a freshly dealt pass once the cursor reaches the end. */
    rollIfExhausted() {
      if (position < order.length) return
      rolls += 1
      order = [...ASSET_IDS].sort(() => Math.random() - 0.5)
      position = 0
    },
  }
}

/** Images never load in jsdom, so resolve them immediately. */
class FakeImage {
  decoding = 'async'
  onload: (() => void) | null = null
  onerror: (() => void) | null = null

  decode(): Promise<void> {
    return Promise.resolve()
  }

  set src(_value: string) {
    Promise.resolve().then(() => this.onload?.())
  }
}

async function mountEngine(server: ReturnType<typeof createCycleServer>) {
  const shown: string[] = []
  vi.mocked(reportPlaybackProgress).mockImplementation(async (assetId: string) => {
    shown.push(assetId)
    server.report(assetId)
    return true
  })

  const { result } = renderHook(() =>
    useSlideshowEngine({
      onBootMessage: () => undefined,
      onCycleComplete: async () => {
        server.rollIfExhausted()
        result.current.playlistRef.current = server.playlist()
      },
    }),
  )

  // DisplayPage owns playlistRef and keeps it current; the engine reads its order from there.
  await act(async () => {
    result.current.playlistRef.current = server.playlist()
    await result.current.bootPlaylist(server.playlist(), CONFIG)
  })

  return { shown, engine: result }
}

/** Advances one slide at a time (the engine's own timer drives it) up to the first repeat. */
async function playUntilRepeat(shown: string[], maxSlides: number) {
  while (shown.length < maxSlides) {
    const before = shown.length
    await act(async () => {
      await vi.advanceTimersByTimeAsync(SLIDE_STEP_MS)
    })
    if (shown.length === before) {
      throw new Error(`slideshow stalled after ${shown.length} slides`)
    }
    if (new Set(shown).size !== shown.length) {
      return shown.slice(0, shown.length - 1)
    }
  }
  return shown
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.stubGlobal('Image', FakeImage)
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

describe('useSlideshowEngine', () => {
  it('plays every photograph in the served cycle before any repeat', async () => {
    const server = createCycleServer()
    const { shown, engine } = await mountEngine(server)

    const uniqueRun = await playUntilRepeat(shown, ASSET_COUNT * 2)

    expect(uniqueRun).toHaveLength(ASSET_COUNT)
    expect(new Set(uniqueRun)).toEqual(new Set(ASSET_IDS))
    expect(server.rolls()).toBeGreaterThanOrEqual(1)
  }, 30_000)

  it('asks for a new cycle at the end of a pass instead of wrapping locally', async () => {
    const server = createCycleServer()
    const { shown } = await mountEngine(server)

    // A full pass shows everything once, and the client has not wrapped anywhere.
    await playUntilRepeat(shown, ASSET_COUNT)
    expect(new Set(shown).size).toBe(ASSET_COUNT)
    expect(server.rolls()).toBe(0)

    // The next advance hits the boundary and asks the backend to deal the next pass.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(SLIDE_STEP_MS)
    })
    expect(server.rolls()).toBe(1)
  }, 30_000)

  it('resumes at the position the backend reports', async () => {
    const server = createCycleServer()
    // Twenty photographs have already been shown, as recorded server-side.
    server.advanceTo(20)

    const { shown } = await mountEngine(server)

    expect(shown[0]).toBe(server.orderAt(20))
  })

  it('does not restart the pass when re-booting mid-cycle', async () => {
    const server = createCycleServer()
    const { shown, engine } = await mountEngine(server)

    // Show ten photographs, then re-anchor the way DisplayPage does when the current photograph has
    // left the playlist. Re-booting must not discard the rest of the pass.
    while (shown.length < 10) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(SLIDE_STEP_MS)
      })
    }
    expect(new Set(shown).size).toBe(10)

    await act(async () => {
      engine.current.playlistRef.current = server.playlist()
      await engine.current.bootPlaylist(server.playlist(), CONFIG)
    })

    const uniqueRun = await playUntilRepeat(shown, ASSET_COUNT)

    expect(new Set(uniqueRun).size).toBe(ASSET_COUNT)
  }, 30_000)

  it('does not consume a photograph while a transition is in flight', async () => {
    const server = createCycleServer()
    const { shown, engine } = await mountEngine(server)
    const committed = [...shown]

    engine.current.transitionRef.current = true
    await act(async () => {
      await engine.current.advanceToNext()
    })

    // The advance was deferred instead of burning a position in the cycle.
    expect(shown).toEqual(committed)
  })
})
