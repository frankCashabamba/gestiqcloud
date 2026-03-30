import React, { useEffect, useState } from 'react'

declare const __APP_BUILD_ID__: string
declare const __APP_VERSION__: string

export default function BuildBadge() {
  const [info, setInfo] = useState<{ buildId: string; version: string }>({ buildId: __APP_BUILD_ID__, version: __APP_VERSION__ })

  useEffect(() => {
    const onMsg = (e: MessageEvent) => {
      const d = e.data || {}
      if (d.type === 'APP_VERSION' && (d.buildId || d.version)) {
        setInfo((prev) => ({ buildId: d.buildId || prev.buildId, version: d.version || prev.version }))
      }
    }
    navigator.serviceWorker?.addEventListener('message', onMsg)
    return () => navigator.serviceWorker?.removeEventListener('message', onMsg)
  }, [])

  return (
    <div
      title={`Build: ${info.buildId}`}
      style={{
        position: 'fixed',
        right: 14,
        bottom: 14,
        zIndex: 40,
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: '0.02em',
        color: '#64748b',
        background: 'rgba(248,250,252,0.9)',
        padding: '3px 8px',
        borderRadius: 20,
        border: '1px solid #e2e8f0',
        backdropFilter: 'blur(6px)',
        userSelect: 'none',
        cursor: 'default',
        pointerEvents: 'auto',
      }}
    >
      v{info.version}
    </div>
  )
}
