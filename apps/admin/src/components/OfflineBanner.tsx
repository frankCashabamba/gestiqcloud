import React, { useEffect, useRef, useState } from 'react'
import { sendTelemetry } from '../lib/telemetry'

type Notice = { kind: 'info' | 'success' | 'warning'; text: string }

export default function OfflineBanner() {
  const [notice, setNotice] = useState<Notice | null>(null)
  const timer = useRef<number | null>(null)

  useEffect(() => {
    const show = (n: Notice, ms = 4000) => {
      setNotice(n)
      if (timer.current) window.clearTimeout(timer.current)
      timer.current = window.setTimeout(() => setNotice(null), ms)
    }

    const onMsg = (e: MessageEvent) => {
      const data = e.data || {}
      if (data.type === 'OUTBOX_QUEUED') {
        show({ kind: 'warning', text: 'Acción guardada offline. Se sincronizará al reconectarse.' })
        sendTelemetry('outbox_queued')
      }
      if (data.type === 'OUTBOX_SYNCED') {
        const ok = data.ok || 0
        const fail = data.fail || 0
        if (ok > 0) {
          show({ kind: 'success', text: `Sincronización completada: ${ok} enviadas${fail ? `, ${fail} pendientes` : ''}.` }, 5000)
          sendTelemetry('outbox_synced', { ok, fail, deferred: data.deferred || 0 })
        }
      }
    }

    const onOnline = () => {
      show({ kind: 'info', text: 'Conectado. Sincronizando…' }, 2500)
      if ('serviceWorker' in navigator) {
        navigator.serviceWorker.ready.then((reg) => reg.active?.postMessage({ type: 'SYNC_NOW' }))
      }
      sendTelemetry('app_online')
    }
    const onOffline = () => { show({ kind: 'warning', text: 'Sin conexión. Trabajarás en modo offline.' }, 3000); sendTelemetry('app_offline') }

    navigator.serviceWorker?.addEventListener('message', onMsg)
    window.addEventListener('online', onOnline)
    window.addEventListener('offline', onOffline)
    return () => {
      navigator.serviceWorker?.removeEventListener('message', onMsg)
      window.removeEventListener('online', onOnline)
      window.removeEventListener('offline', onOffline)
      if (timer.current) window.clearTimeout(timer.current)
    }
  }, [])

  if (!notice) return null

  const bg = notice.kind === 'success' ? '#065f46' : notice.kind === 'warning' ? '#92400e' : '#334155'
  const border = notice.kind === 'success' ? '#34d399' : notice.kind === 'warning' ? '#fbbf24' : '#94a3b8'

  return (
    <div style={{
      position: 'fixed', left: 12, right: 12, bottom: 12, zIndex: 1000,
      background: bg, color: 'white', padding: '10px 12px', borderRadius: 8,
      border: `1px solid ${border}`, boxShadow: '0 6px 18px rgba(0,0,0,.18)',
      fontSize: 14
    }}>
      {notice.text}
    </div>
  )
}
