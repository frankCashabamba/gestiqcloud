import React, { Suspense, useEffect, useState } from 'react'
import { Navigate, useParams } from 'react-router-dom'

type LazyComp = React.LazyExoticComponent<React.ComponentType<any>>

// Descubre plantillas disponibles en ../plantillas/*.tsx
const PLANTILLAS = import.meta.glob('../plantillas/*.tsx')

export default function PlantillaLoader() {
  const { slug } = useParams()
  const [Component, setComponent] = useState<LazyComp | null>(null)
  const [accesoDenegado, setAccesoDenegado] = useState(false)

  useEffect(() => {
    let mounted = true
    if (!slug) { setAccesoDenegado(true); return }

    try { document.documentElement.dataset.sector = slug } catch {}
    const plantilla = slug
    ;(async () => {
      try {
        const key = `../plantillas/${plantilla}.tsx`
        const importer = (PLANTILLAS as any)[key]
        let lazy: LazyComp | null = null
        if (importer) {
          lazy = React.lazy(importer as any)
        } else {
          lazy = React.lazy(async () => ({
            default: () => <div className="p-10 text-center">Plantilla por defecto para “{slug}”.</div>
          }))
        }
        if (mounted) setComponent(lazy)
      } catch {
        if (mounted) setComponent(null)
      }
    })()
    return () => { mounted = false }
  }, [slug])

  if (!slug || accesoDenegado) return <Navigate to="/unauthorized" replace />
  if (!Component) return <div className="p-10 text-center text-red-600">No se pudo cargar ninguna plantilla</div>

  return (
    <Suspense fallback={<div className="p-10 text-center">Cargando plantilla...</div>}>
      <Component slug={slug} />
    </Suspense>
  )
}

