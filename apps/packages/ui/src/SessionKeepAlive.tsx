import React, { useEffect, useRef, useState } from 'react'

export type UseAuthLike = () => {
  token: string | null
  refresh: () => Promise<boolean>
  logout: () => Promise<void>
}

export type SessionKeepAliveProps = {
  useAuth: UseAuthLike
  warnAfterMs?: number
  responseWindowMs?: number
  messages?: {
    title?: string
    bodyPrefix?: string
    secondsSuffix?: string
    question?: string
    exit?: string
    stay?: string
  }
}

const defaultMsgs = {
  title: 'Sesión a punto de expirar',
  bodyPrefix: 'Tu sesión expirará en',
  secondsSuffix: 's',
  question: '¿Quieres seguir dentro?',
  exit: 'Salir',
  stay: 'Seguir conectado',
}

export function SessionKeepAlive({
  useAuth,
  warnAfterMs = 300 * 60_000,
  responseWindowMs = 60_000,
  messages,
}: SessionKeepAliveProps) {
  const { token, refresh, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const [remaining, setRemaining] = useState(Math.floor(responseWindowMs / 1000))
  const [rev, setRev] = useState(0)

  const warnTimer = useRef<number | null>(null)
  const autoTimer = useRef<number | null>(null)
  const tickTimer = useRef<number | null>(null)

  const clearAll = () => {
    if (warnTimer.current) window.clearTimeout(warnTimer.current)
    if (autoTimer.current) window.clearTimeout(autoTimer.current)
    if (tickTimer.current) window.clearInterval(tickTimer.current)
    warnTimer.current = autoTimer.current = tickTimer.current = null
  }

  useEffect(() => {
    if (!token) return
    clearAll()
    warnTimer.current = window.setTimeout(() => {
      setOpen(true)
      setRemaining(Math.floor(responseWindowMs / 1000))
      tickTimer.current = window.setInterval(() => setRemaining((s) => (s > 0 ? s - 1 : 0)), 1000)
      autoTimer.current = window.setTimeout(async () => {
        setOpen(false)
        clearAll()
        await logout()
      }, responseWindowMs)
    }, warnAfterMs)
    return clearAll
  }, [token, warnAfterMs, responseWindowMs, logout])

  // Reinicia timers con actividad (throttle)
  useEffect(() => {
    if (!token) return
    let last = 0
    const throttleMs = 5000  // Reduced frequency from 1s to 5s
    const handler = () => {
      const now = Date.now()
      if (now - last < throttleMs) return
      last = now
      clearAll()
      if (open) setOpen(false)
      setRemaining(Math.floor(responseWindowMs / 1000))
      setRev((x) => x + 1)
    }
    const events = ['click', 'keydown'] as const  // Only essential events
    events.forEach((ev) => window.addEventListener(ev, handler, { passive: true }))
    return () => events.forEach((ev) => window.removeEventListener(ev, handler as any))
  }, [token, responseWindowMs, open])

  const onContinue = async () => {
    clearAll()
    const ok = await refresh()
    if (!ok) return logout()
    setOpen(false)
    setRev((x) => x + 1)
  }
  const onExit = async () => {
    clearAll()
    setOpen(false)
    await logout()
  }

  if (!open) return null
  const t = { ...defaultMsgs, ...(messages || {}) }

  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-semibold text-gray-800">{t.title}</h2>
        <p className="text-sm text-gray-600 mt-2">
          {t.bodyPrefix} <span className="font-semibold">{remaining}{t.secondsSuffix}</span>. {t.question}
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <button onClick={onExit} className="px-4 py-2 rounded-lg bg-gray-200 hover:bg-gray-300 text-gray-800 text-sm">
            {t.exit}
          </button>
          <button onClick={onContinue} className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm">
            {t.stay}
          </button>
        </div>
      </div>
    </div>
  )
}
