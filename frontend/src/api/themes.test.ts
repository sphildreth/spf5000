import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ThemesResponse } from './types'
import { apiGet } from './http'
import { clearThemesCache, getThemes } from './themes'

vi.mock('./http', () => ({
  apiGet: vi.fn(),
}))

const RESPONSE: ThemesResponse = {
  active_theme_id: 'default-dark',
  home_city_accent_style: 'default',
  themes: [],
}

describe('getThemes', () => {
  beforeEach(() => {
    clearThemesCache()
    vi.mocked(apiGet).mockResolvedValue(RESPONSE)
  })

  afterEach(() => {
    clearThemesCache()
    vi.clearAllMocks()
  })

  it('reuses the cached response across repeated calls', async () => {
    await getThemes()
    await getThemes()

    expect(apiGet).toHaveBeenCalledTimes(1)
  })

  it('deduplicates concurrent callers against the same in-flight request', async () => {
    const [first, second] = await Promise.all([getThemes(), getThemes()])

    expect(apiGet).toHaveBeenCalledTimes(1)
    expect(first).toBe(second)
  })

  it('forces a fresh fetch when requested', async () => {
    await getThemes()
    await getThemes({ force: true })

    expect(apiGet).toHaveBeenCalledTimes(2)
  })
})
