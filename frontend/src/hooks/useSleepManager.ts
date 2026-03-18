import { useCallback, useRef, useState } from 'react'
import type { SleepSchedule } from '../api/types'


function getCurrentMinutesForSchedule(_schedule: SleepSchedule): number {
  const now = new Date()
  return now.getHours() * 60 + now.getMinutes()
}

export function isInSleepWindow(schedule: SleepSchedule): boolean {
  if (!schedule.sleep_schedule_enabled) {
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
  }
}
