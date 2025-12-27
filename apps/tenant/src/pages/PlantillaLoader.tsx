import React, { Suspense, useEffect, useState } from 'react'
import { Navigate, useParams } from 'react-router-dom'

type LazyComp = React.LazyExoticComponent<React.ComponentType<any>>

const PLANTILLAS = import.meta.glob('../plantillas/*.tsx')

export default function PlantillaLoader() {
  const { slug } = useParams()
  const [Component, setComponent] = useState<LazyComp | null>(null)
  const [accessDenied, setAccessDenied] = useState(false)

  useEffect(() => {
    let mounted = true
    if (!slug) {
      setAccessDenied(true)
      return
    }

    try {
      document.documentElement.dataset.sector = slug
    } catch {}
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
            default: () => <div className="p-10 text-center">Default template for "{slug}".</div>,
          }))
        }
        if (mounted) setComponent(lazy)
      } catch {
        if (mounted) setComponent(null)
      }
    })()
    return () => {
      mounted = false
    }
  }, [slug])

  if (!slug || accessDenied) return <Navigate to="/unauthorized" replace />
  if (!Component) return <div className="p-10 text-center text-red-600">Unable to load template</div>

  return (
    <Suspense fallback={<div className="p-10 text-center">Loading template...</div>}>
      <Component slug={slug} />
    </Suspense>
  )
}
