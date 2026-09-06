import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getDisplayConfig } from '../api/display'
import { getCollections } from '../api/collections'
import { getSettingsTimeReference, getSleepSchedule } from '../api/settings'
import { getDefaultDisplayConfig } from '../api/display'
import type {
  CollectionSummary,
  DisplayConfig,
  SettingsTimeReference,
  SleepSchedule,
} from '../api/types'
import { DisplaySettingsPage } from './DisplaySettingsPage'

vi.mock('../api/collections', () => ({ getCollections: vi.fn() }))
vi.mock('../api/display', async () => {
  const actual = await vi.importActual<typeof import('../api/display')>('../api/display')
  return {
    ...actual,
    getDisplayConfig: vi.fn(),
    refreshDisplayCache: vi.fn(),
    updateDisplayConfig: vi.fn(),
  }
})
vi.mock('../api/settings', () => ({
  getSettingsTimeReference: vi.fn(),
  getSleepSchedule: vi.fn(),
  updateSleepSchedule: vi.fn(),
}))

const COLLECTION: CollectionSummary = {
  id: 'collection-1',
  name: 'Family',
  source_ids: [],
  is_active: true,
}

const SLEEP_SCHEDULE: SleepSchedule = {
  sleep_schedule_enabled: false,
  sleep_start_local_time: '22:00',
  sleep_end_local_time: '07:00',
  display_timezone: null,
}

const TIME_REFERENCE: SettingsTimeReference = {
  current_server_utc_timestamp: '2026-01-01T00:00:00+00:00',
  pi_local_timezone: 'UTC',
  configured_display_timezone: null,
  effective_display_timezone: 'UTC',
  available_timezones: ['UTC', 'America/New_York'],
}

function mockApis(config: Partial<DisplayConfig>) {
  vi.mocked(getDisplayConfig).mockResolvedValue({
    ...getDefaultDisplayConfig(),
    ...config,
  })
  vi.mocked(getCollections).mockResolvedValue([COLLECTION])
  vi.mocked(getSleepSchedule).mockResolvedValue(SLEEP_SCHEDULE)
  vi.mocked(getSettingsTimeReference).mockResolvedValue(TIME_REFERENCE)
}

async function renderPage() {
  render(<DisplaySettingsPage />)
  return screen.findByText('Shuffle playlist order')
}

function bagToggle(): HTMLInputElement {
  return screen.getByRole('checkbox', {
    name: /show every photo before repeating/i,
  }) as HTMLInputElement
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('DisplaySettingsPage playback controls', () => {
  it('offers a shuffle-bag toggle alongside shuffle', async () => {
    mockApis({ shuffle_enabled: true, shuffle_bag_enabled: true })
    await renderPage()

    const shuffle = screen.getByRole('checkbox', {
      name: /shuffle playlist order/i,
    }) as HTMLInputElement
    expect(shuffle).toBeChecked()
    expect(bagToggle()).toBeChecked()
    expect(bagToggle()).toBeEnabled()
    await waitFor(() => expect(getDisplayConfig).toHaveBeenCalled())
  })

  it('disables the bag toggle when playback is not shuffled', async () => {
    mockApis({ shuffle_enabled: false, shuffle_bag_enabled: true })
    await renderPage()

    expect(bagToggle()).toBeDisabled()
  })

  it('summarises repeat handling for the bag being off', async () => {
    mockApis({ shuffle_enabled: true, shuffle_bag_enabled: false })
    await renderPage()

    expect(screen.getByText('Random with repeats')).toBeInTheDocument()
    expect(
      screen.getByText(/can appear again before every other photo/i),
    ).toBeInTheDocument()
  })

  it('summarises repeat handling for the default bag', async () => {
    mockApis({ shuffle_enabled: true, shuffle_bag_enabled: true })
    await renderPage()

    expect(screen.getByText('Show all before repeating')).toBeInTheDocument()
    expect(
      screen.getByText(/shown once before any repeat/i),
    ).toBeInTheDocument()
  })
})
