import { useEffect, useState } from 'react'

import loadingArtworkUrl from '../../../graphics/loading.png'

export type BootScreenTone = 'booting' | 'empty' | 'error'

export interface BootScreenMessage {
  title: string
  detail?: string
  secondary?: string
  kicker?: string
  tone?: BootScreenTone
  animateDots?: boolean
}

export interface BootScreenDemoFrame extends BootScreenMessage {
  durationMs?: number
}

interface BootScreenProps {
  message: BootScreenMessage
}

const DOTS_SEQUENCE = ['', '.', '..', '...']

export function BootScreen({ message }: BootScreenProps) {
  const dots = useAnimatedDots(Boolean(message.animateDots))
  const tone = message.tone ?? 'booting'

  return (
    <div className={`display-boot-screen display-boot-screen--${tone}`} role={tone === 'error' ? 'alert' : 'status'} aria-live="polite">
      <div className="display-boot-artwork" aria-hidden="true">
        <img src={loadingArtworkUrl} alt="" draggable={false} />
      </div>

      <div className="display-boot-copy">
        <p className="display-boot-kicker">{message.kicker ?? 'SPF5000'}</p>
        <h1 aria-label={message.title}>
          {message.title}
          {message.animateDots ? <span aria-hidden="true">{dots}</span> : null}
        </h1>
        {message.detail ? <p className="display-boot-detail">{message.detail}</p> : null}
        {message.secondary ? <p className="display-boot-secondary">{message.secondary}</p> : null}
      </div>
    </div>
  )
}

export function useBootScreenDemo(enabled: boolean, frames: BootScreenDemoFrame[]): BootScreenMessage | null {
  const [index, setIndex] = useState(0)

  useEffect(() => {
    if (!enabled || frames.length === 0) {
      setIndex(0)
      return
    }

    const currentFrame = frames[index] ?? frames[0]
    const timer = window.setTimeout(() => {
      setIndex((currentIndex) => (currentIndex + 1) % frames.length)
    }, currentFrame.durationMs ?? 1800)

    return () => window.clearTimeout(timer)
  }, [enabled, frames, index])

  if (!enabled || frames.length === 0) {
    return null
  }

  const currentFrame = frames[index] ?? frames[0]
  return {
    title: currentFrame.title,
    detail: currentFrame.detail,
    secondary: currentFrame.secondary,
    kicker: currentFrame.kicker,
    tone: currentFrame.tone,
    animateDots: currentFrame.animateDots,
  }
}

function useAnimatedDots(enabled: boolean): string {
  const [sequenceIndex, setSequenceIndex] = useState(0)

  useEffect(() => {
    if (!enabled) {
      setSequenceIndex(0)
      return
    }

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReducedMotion) {
      setSequenceIndex(DOTS_SEQUENCE.length - 1)
      return
    }

    const timer = window.setInterval(() => {
      setSequenceIndex((currentIndex) => (currentIndex + 1) % DOTS_SEQUENCE.length)
    }, 450)

    return () => window.clearInterval(timer)
  }, [enabled])

  return DOTS_SEQUENCE[sequenceIndex] ?? ''
}
