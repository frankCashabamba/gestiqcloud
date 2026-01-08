import React, { Suspense, useEffect, useMemo, useState } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import { useI18n } from '../i18n/I18nProvider'
import { useMisModulos } from '../hooks/useMisModulos'

// Convención: cada módulo expone ./<modulo>/Routes.tsx (preferido) o ./<modulo>/Panel.tsx
// Ejemplos: contabilidad/Panel.tsx, inventario/Panel.tsx, ventas/Routes.tsx, etc.

// Nota: las rutas de Vite en import.meta.glob son relativas a este archivo
const ROUTES = import.meta.glob('./*/Routes.tsx')
const PANELS = import.meta.glob('./*/Panel.tsx')

// Alias opcionales por compatibilidad (slug viejo -> carpeta nueva)
const ALIASES: Record<string, string> = {
  // Rutas legacy -> carpeta real
  imports: 'importador',
  reports: 'reportes',
}

export default function ModuleLoader() {
  const { mod } = useParams()
  const [Component, setComponent] = useState<React.ComponentType<any> | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const { t } = useI18n()
  const { allowedSlugs, loading } = useMisModulos()

  const folder = useMemo(() => {
    if (!mod) return ''
    const norm = mod.toLowerCase()
    return ALIASES[norm] || norm
  }, [mod])
  const allowedSlug = useMemo(() => {
    if (!mod) return ''
    const norm = mod.toLowerCase()
    const alias = Object.entries(ALIASES).find(([, v]) => v === folder)?.[0]
    return alias || norm
  }, [mod, folder])
  const keyRoutes = useMemo(() => (folder ? `./${folder}/Routes.tsx` : ''), [folder])
  const keyPanel = useMemo(() => (folder ? `./${folder}/Panel.tsx` : ''), [folder])

  useEffect(() => {
    let cancelled = false
    setLoadError(null)
    async function load() {
      if (!mod) return
      const importer = (ROUTES as any)[keyRoutes] || (PANELS as any)[keyPanel]
      if (!importer) {
        if (!cancelled) {
          setLoadError('not-found')
          setComponent(null)
        }
        return
      }
      try {
        const modImp: any = await importer()
        if (!cancelled) setComponent(() => modImp.default || modImp)
      } catch (e) {
        if (!cancelled) {
          console.error('Error cargando módulo', e)
          setLoadError('load-error')
          setComponent(null)
        }
      }
    }
    load()
    return () => { cancelled = true }
  }, [mod, keyRoutes, keyPanel])

  if (!mod) return <Navigate to="/error" replace />
  if (loading) return <div style={{ padding: 16 }}>{t('common:loading.module')}</div>
  const bypass = folder === 'contabilidad' || folder === 'finanzas'
  if (folder && !bypass && !(allowedSlugs.has(folder) || allowedSlugs.has(allowedSlug))) return <Navigate to="/unauthorized" replace />
  if (loadError === 'not-found') return <div style={{ padding: 16 }}>Module not found.</div>
  if (loadError === 'load-error') return <div style={{ padding: 16 }}>Error loading module.</div>
  if (!Component) return <div style={{ padding: 16 }}>{t('common:loading.module')}</div>

  return (
    <Suspense fallback={<div style={{ padding: 16 }}>{t('common:loading.module')}</div>}>
      <Component />
    </Suspense>
  )
}
