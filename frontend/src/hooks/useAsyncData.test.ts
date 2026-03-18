import { describe, expect, it, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useAsyncData } from '../hooks/useAsyncData'

describe('useAsyncData', () => {
  it('starts with loading true and no data', () => {
    const { result } = renderHook(() =>
      useAsyncData(async () => ({ value: 1 }), []),
    )
    expect(result.current.loading).toBe(true)
    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('loads data successfully', async () => {
    const { result } = renderHook(() =>
      useAsyncData(async () => ({ value: 42 }), []),
    )
    await vi.waitFor(() =>
      expect(result.current.loading).toBe(false),
    )
    expect(result.current.data).toEqual({ value: 42 })
    expect(result.current.error).toBeNull()
  })

  it('captures errors', async () => {
    const { result } = renderHook(() =>
      useAsyncData(async () => { throw new Error('load failed') }, []),
    )
    await vi.waitFor(() =>
      expect(result.current.loading).toBe(false),
    )
    expect(result.current.data).toBeNull()
    expect(result.current.error).toBe('load failed')
  })

  it('converts non-Error throws to string', async () => {
    const { result } = renderHook(() =>
      useAsyncData(async () => { throw 'string error' }, []),
    )
    await vi.waitFor(() =>
      expect(result.current.loading).toBe(false),
    )
    expect(result.current.error).toBe('string error')
  })

  it('reload calls the loader again', async () => {
    let callCount = 0
    const { result } = renderHook(() =>
      useAsyncData(async () => { callCount++; return { count: callCount } }, []),
    )
    await vi.waitFor(() =>
      expect(result.current.loading).toBe(false),
    )
    expect(result.current.data).toEqual({ count: 1 })

    await result.current.reload()
    await vi.waitFor(() =>
      expect(result.current.loading).toBe(false),
    )
    expect(result.current.data).toEqual({ count: 2 })
  })

  it('setData allows direct data update', async () => {
    const { result } = renderHook(() =>
      useAsyncData(async () => ({ value: 1 }), []),
    )
    await vi.waitFor(() =>
      expect(result.current.loading).toBe(false),
    )
    result.current.setData({ value: 99 })
    expect(result.current.data).toEqual({ value: 99 })
  })

  it('respects dependency array changes', async () => {
    const { result, rerender } = renderHook(
      ({ id }: { id: number }) =>
        useAsyncData(async () => ({ id }), [id]),
      { initialProps: { id: 1 } },
    )
    await vi.waitFor(() =>
      expect(result.current.loading).toBe(false),
    )
    expect(result.current.data).toEqual({ id: 1 })

    rerender({ id: 2 })
    await vi.waitFor(() =>
      expect(result.current.loading).toBe(false),
    )
    expect(result.current.data).toEqual({ id: 2 })
  })
})
