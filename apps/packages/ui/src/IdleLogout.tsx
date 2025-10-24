import React from 'react'

type Props = {
  timeoutMs?: number
  onLogout: () => void
  events?: string[]
}

export default function IdleLogout({ timeoutMs = 15 * 60_000, onLogout, events = ['mousemove','keydown','click','scroll','touchstart'] }: Props) {
  const timer = React.useRef<number | null>(null)
  const reset = React.useCallback(() => {
    if (timer.current) window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => onLogout(), timeoutMs)
  }, [onLogout, timeoutMs])

  React.useEffect(() => {
    reset()
    for (const ev of events) window.addEventListener(ev, reset, { passive: true })
    return () => {
      if (timer.current) window.clearTimeout(timer.current)
      for (const ev of events) window.removeEventListener(ev, reset as any)
    }
  }, [reset, events])

  return null
}

