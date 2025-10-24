import React, { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { apiFetch } from '../lib/http'

type ThemeResponse = { sector?: string }

export default function SectorRedirect() {
  const [slug, setSlug] = useState<string | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        // Intenta obtener sector desde el tema (puede incluir sector)
        const t = await apiFetch<ThemeResponse>('/v1/tenant/settings/theme')
        const s = (t && t.sector) ? t.sector : 'default'
        if (!cancelled) setSlug(s)
        try { document.documentElement.dataset.sector = s } catch {}
      } catch {
        if (!cancelled) { setSlug('default'); setError(true) }
      }
    })()
    return () => { cancelled = true }
  }, [])

  if (!slug) return <div style={{ padding: 16 }}>Cargando plantilla…€¦</div>
  return <Navigate to={`/plantilla/${slug}`} replace />
}


