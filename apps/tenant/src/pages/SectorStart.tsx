import React, { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { apiFetch } from '../lib/http'
import { useAuth } from '../auth/AuthContext'
import { fetchTenantTheme } from '../services/theme'

type MeResp = { empresa_slug?: string }
type ThemeResponse = { sector?: string }

export default function SectorStart() {
  const [target, setTarget] = useState<string | null>(null)
  const { token } = useAuth() as { token: string | null }

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        // Prefer empresa_slug from authenticated profile
        if (token) {
          try {
            const me = await apiFetch<MeResp>('/api/v1/me/tenant', { authToken: token })
            if (me?.empresa_slug) {
              if (!cancelled) setTarget(me.empresa_slug)
              return
            }
          } catch {}
        }
        // Fallback to sector (not ideal for vanity, but better than blocking)
        const t = await fetchTenantTheme()
        const s = (t && t.sector) ? t.sector : 'default'
        if (!cancelled) setTarget(s)
        try { document.documentElement.dataset.sector = s } catch {}
      } catch {
        if (!cancelled) setTarget('default')
      }
    })()
    return () => { cancelled = true }
  }, [token])

  if (!target) return <div style={{ padding: 16 }}>Cargando plantilla…</div>
  return <Navigate to={`/${target}`} replace />
}
