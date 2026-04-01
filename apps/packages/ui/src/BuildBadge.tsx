import React, { useEffect, useState } from 'react'
import { useEnv } from './env'

declare const __APP_BUILD_ID__: string
declare const __APP_VERSION__: string

function buildVersionUrl(rawApiUrl: string): string {
  const fallback = '/api/version'

  try {
    const base = String(rawApiUrl || '').trim()
    if (!base) return fallback

    const url = new URL(base, window.location.origin)
    const normalizedPath = url.pathname.replace(/\/+$/g, '').replace(/\/(?:api(?:\/v1)?|v1)$/i, '')
    url.pathname = `${normalizedPath || ''}/api/version`
    url.search = ''
    url.hash = ''

    if (url.origin === window.location.origin) {
      return url.pathname
    }

    return url.toString()
  } catch {
    return fallback
  }
}

export default function BuildBadge() {
  const env = useEnv()
  const [info, setInfo] = useState<{ buildId: string; version: string }>({ buildId: __APP_BUILD_ID__, version: __APP_VERSION__ })

  useEffect(() => {
    // Fetch live version from DB via backend
    fetch(buildVersionUrl(env.apiUrl))
      .then((r) => r.ok ? r.json() : null)
      .then((d) => { if (d?.version) setInfo((prev) => ({ ...prev, version: d.version })) })
      .catch(() => {})

    // Also listen to service worker updates
    const onMsg = (e: MessageEvent) => {
      const d = e.data || {}
      if (d.type === 'APP_VERSION' && (d.buildId || d.version)) {
        setInfo((prev) => ({ buildId: d.buildId || prev.buildId, version: d.version || prev.version }))
      }
    }
    navigator.serviceWorker?.addEventListener('message', onMsg)
    return () => navigator.serviceWorker?.removeEventListener('message', onMsg)
  }, [env.apiUrl])

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
