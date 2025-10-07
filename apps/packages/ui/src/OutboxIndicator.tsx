import React from 'react'

export default function OutboxIndicator() {
  const [pending, setPending] = React.useState<number>(0)
  const [last, setLast] = React.useState<{ ok: number; fail: number } | null>(null)

  React.useEffect(() => {
    function onMsg(ev: MessageEvent) {
      const m = ev?.data
      if (!m || !m.type) return
      if (m.type === 'OUTBOX_QUEUED') {
        setPending((n) => Math.max(1, n + 1))
      } else if (m.type === 'OUTBOX_SYNCED') {
        setLast({ ok: m.ok ?? 0, fail: m.fail ?? 0 })
        setPending((n) => Math.max(0, n - (m.ok ?? 0)))
      }
    }
    window.addEventListener('message', onMsg)
    return () => window.removeEventListener('message', onMsg)
  }, [])

  const visible = pending > 0 || (last && last.fail > 0)
  if (!visible) return null

  const onClick = () => {
    try {
      if (navigator?.serviceWorker?.controller) {
        navigator.serviceWorker.controller.postMessage({ type: 'SYNC_NOW' })
      }
    } catch {}
  }

  return (
    <button
      onClick={onClick}
      title={last ? `Pendientes: ${pending} · Último sync OK:${last.ok} FAIL:${last.fail}` : `Pendientes: ${pending}`}
      style={{
        position: 'fixed',
        right: 12,
        bottom: 12,
        zIndex: 50,
        background: last && last.fail > 0 ? '#f43f5e' : '#0ea5e9',
        color: '#fff',
        borderRadius: 9999,
        padding: '8px 12px',
        boxShadow: '0 6px 16px rgba(0,0,0,.2)',
        fontSize: 12,
        fontWeight: 600,
      }}
    >
      {pending > 0 ? `Pendientes ${pending}` : 'Reintentar sync'}
    </button>
  )
}

