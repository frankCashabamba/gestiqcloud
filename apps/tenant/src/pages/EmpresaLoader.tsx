import React, { Suspense, useEffect, useState } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import { applyTheme } from '@shared/ui'
import { useAuth } from '../auth/AuthContext'
import { fetchCompanyTheme } from '../services/theme'

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
        const t = await fetchCompanyTheme(empresa)
        if (t) {
          try {
            applyTheme(t as any)
          } catch {}
          const s = t.sector || 'default'
          try {
            document.documentElement.dataset.sector = s
          } catch {}
          if (!cancelled) setSector(s)
        }
      } catch {
        // ignore
      } finally {
        if (!cancelled) setReady(true)
      }
    })()
    return () => {
      cancelled = true
    }
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
          lazy = React.lazy(() => import('../plantillas/default'))
        }
        if (mounted) setComponent(lazy)
      } catch {
        if (mounted) setComponent(React.lazy(() => import('../plantillas/default')))
      }
    })()
    return () => {
      mounted = false
    }
  }, [sector, empresa])

  try {
    const dec = empresa ? decodeURIComponent(empresa) : ''
    if (dec && dec.startsWith(':')) {
      const slug = profile?.empresa_slug
      return <Navigate to={slug ? `/${slug}` : `/`} replace />
    }
  } catch {}

  if (!empresa) return <Navigate to="/error" replace />
  if (!ready || !Component) return <div className="p-10 text-center">Loading template...</div>

  return (
    <Suspense fallback={<div className="p-10 text-center">Loading template...</div>}>
      <Component slug={sector ?? 'default'} />
    </Suspense>
  )
}
