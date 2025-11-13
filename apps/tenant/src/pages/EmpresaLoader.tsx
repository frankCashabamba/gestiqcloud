import React, { Suspense, useEffect, useMemo, useState } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import { apiFetch } from '../lib/http'
import { applyTheme } from '@shared/ui'
import { useAuth } from '../auth/AuthContext'

type LazyComp = React.LazyExoticComponent<React.ComponentType<any>>
type ThemeResp = { sector?: string } & Record<string, any>

const PLANTILLAS = import.meta.glob('../plantillas/*.tsx')

export default function EmpresaLoader() {
  const { empresa } = useParams()
  const { profile } = useAuth()
  const [Component, setComponent] = useState<LazyComp | null>(null)
  const [ready, setReady] = useState(false)
  const [sector, setSector] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        if (!empresa) return
        const t = await apiFetch<ThemeResp>(`/api/v1/tenant/settings/theme?empresa=${encodeURIComponent(empresa)}`)
        if (t) {
          try { applyTheme(t as any) } catch {}
          const s = t.sector || 'default'
          try { document.documentElement.dataset.sector = s } catch {}
          if (!cancelled) setSector(s)
        }
      } catch {}
      finally {
        if (!cancelled) setReady(true)
      }
    })()
    return () => { cancelled = true }
  }, [empresa])

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const name = sector || 'default'
        const key = `../plantillas/${name}.tsx`
        const importer = (PLANTILLAS as any)[key]
        let lazy: LazyComp
        if (importer) {
          lazy = React.lazy(importer as any)
        } else {
          // Fallback profesional: carga plantilla default.tsx
          lazy = React.lazy(() => import('../plantillas/default'))
        }
        if (mounted) setComponent(lazy)
      } catch {
        // último recurso: también cargar default.tsx
        if (mounted) setComponent(React.lazy(() => import('../plantillas/default')))
      }
    })()
    return () => { mounted = false }
  }, [sector, empresa])

  // Si el valor de la URL es literalmente ':empresa' (o está URL-encoded), redirige a un slug real o a raíz
  try {
    const dec = empresa ? decodeURIComponent(empresa) : ''
    if (dec && dec.startsWith(':')) {
      const slug = profile?.empresa_slug
      return <Navigate to={slug ? `/${slug}` : `/`} replace />
    }
  } catch {}

  if (!empresa) return <Navigate to="/error" replace />
  if (!ready || !Component) return <div className="p-10 text-center">Cargando plantilla…</div>

  return (
    <Suspense fallback={<div className="p-10 text-center">Cargando plantilla…</div>}>
      <Component slug={sector ?? 'default'} />
    </Suspense>
  )
}
