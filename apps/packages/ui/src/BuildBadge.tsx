import React, { useEffect, useState } from 'react'

declare const __APP_BUILD_ID__: string
declare const __APP_VERSION__: string

export default function BuildBadge() {
  const [info, setInfo] = useState<{ buildId: string; version: string }>({ buildId: __APP_BUILD_ID__, version: __APP_VERSION__ })

  useEffect(() => {
    const onMsg = (e: MessageEvent) => {
      const d = e.data || {}
      if (d.type === 'APP_VERSION' && (d.buildId || d.version)) {
        setInfo({ buildId: d.buildId || info.buildId, version: d.version || info.version })
      }
    }
    navigator.serviceWorker?.addEventListener('message', onMsg)
    return () => navigator.serviceWorker?.removeEventListener('message', onMsg)
  }, [])

  return (
    <div style={{ position: 'fixed', left: 12, bottom: 12, zIndex: 999, fontSize: 11, color: '#94a3b8', background: 'rgba(15,23,42,.75)', padding: '4px 8px', borderRadius: 6, border: '1px solid #1f2937' }}>
      v{info.version} · {info.buildId}
    </div>
  )
}

