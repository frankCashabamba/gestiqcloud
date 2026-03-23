import React, { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/AuthContext'
import { fetchCompanyTheme } from '../services/theme'

type ThemeResponse = { sector?: string }

export default function SectorStart() {
  const { t: tr } = useTranslation()
  const [target, setTarget] = useState<string | null>(null)
  const { token, profile, loading: authLoading } = useAuth()

  useEffect(() => {
    // Si el profile ya está cargado con empresa_slug, lo usamos directamente
    // sin hacer fetch extra a /me/tenant
    if (profile?.empresa_slug) {
      setTarget(profile.empresa_slug)
      return
    }

    // Mientras auth carga, esperar
    if (authLoading) return

    let cancelled = false
    ;(async () => {
      try {
        // Fallback a tema de empresa si no hay slug en el profile
        const t = await fetchCompanyTheme()
        const s = (t && (t as ThemeResponse).sector) ? (t as ThemeResponse).sector! : 'default'
        if (!cancelled) setTarget(s)
        try { document.documentElement.dataset.sector = s } catch {}
      } catch {
        if (!cancelled) setTarget('default')
      }
    })()
    return () => { cancelled = true }
  }, [token, profile, authLoading])

  if (!target) return <div style={{ padding: 16 }}>{tr('pages.sectorStart.loadingTemplate')}</div>
  return <Navigate to={`/${target}`} replace />
}
