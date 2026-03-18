import { useCallback, useRef, useState } from 'react'
import type { SleepSchedule } from '../api/types'

function normalizeDisplayTimezone(value: string | null | undefined): string | null {
  const normalized = value?.trim() ?? ''
  return normalized.length > 0 ? normalized : null
}

function getCurrentMinutesInTimezone(now: Date, timeZone: string): number {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone,
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(now)

  const hour = Number(parts.find((part) => part.type === 'hour')?.value ?? Number.NaN)
  const minute = Number(parts.find((part) => part.type === 'minute')?.value ?? Number.NaN)

  if (!Number.isFinite(hour) || !Number.isFinite(minute)) {
    throw new RangeError(`Could not resolve time for timezone: ${timeZone}`)
  }

  return hour * 60 + minute
}

function getCurrentMinutesForSchedule(schedule: SleepSchedule, now = new Date()): number {
  const displayTimezone = normalizeDisplayTimezone(schedule.display_timezone)
  if (!displayTimezone) {
    return now.getHours() * 60 + now.getMinutes()
  }

  try {
    return getCurrentMinutesInTimezone(now, displayTimezone)
  } catch {
    return now.getHours() * 60 + now.getMinutes()
  }
}

export function isInSleepWindow(schedule: SleepSchedule | null): boolean {
  if (!schedule || !schedule.sleep_schedule_enabled) {
    return false
  }

  const currentMinutes = getCurrentMinutesForSchedule(schedule)

  const [startH = 0, startM = 0] = schedule.sleep_start_local_time.split(':').map(Number)
  const [endH = 0, endM = 0] = schedule.sleep_end_local_time.split(':').map(Number)
  const startMinutes = startH * 60 + startM
  const endMinutes = endH * 60 + endM

  if (startMinutes === endMinutes) {
    return false
  }

  if (startMinutes < endMinutes) {
    return currentMinutes >= startMinutes && currentMinutes < endMinutes
  }

  return currentMinutes >= startMinutes || currentMinutes < endMinutes
}

export function describeSleepSchedule(schedule: SleepSchedule | null): string {
  if (!schedule?.sleep_schedule_enabled) {
    return 'No quiet hours are active for this frame.'
  }

  const displayTimezone = normalizeDisplayTimezone(schedule.display_timezone)
  const timezoneLabel = displayTimezone ? `${displayTimezone} time` : 'the display device local time'

  return `Quiet hours ${schedule.sleep_start_local_time} → ${schedule.sleep_end_local_time} use ${timezoneLabel}.`
}


interface SleepManagerOptions {
  onWake?: () => void
  onSleep?: () => void
}

export function useSleepManager(options: SleepManagerOptions = {}) {
  const [isSleeping, setIsSleeping] = useState(false)
  const isSleepingRef = useRef(false)

  const updateSleepState = useCallback(
    (schedule: SleepSchedule | null) => {
      const nowSleeping = schedule ? isInSleepWindow(schedule) : false
      const wasSleeping = isSleepingRef.current

      if (wasSleeping !== nowSleeping) {
        isSleepingRef.current = nowSleeping
        setIsSleeping(nowSleeping)
        if (wasSleeping && !nowSleeping) {
          options.onWake?.()
        } else if (!wasSleeping && nowSleeping) {
          options.onSleep?.()
        }
      }

      return nowSleeping
    },
    [options.onWake, options.onSleep],
  )

  return {
    isSleeping,
    isSleepingRef,
    updateSleepState,
    isInSleepWindow,
    describeSleepSchedule,
  }
}
