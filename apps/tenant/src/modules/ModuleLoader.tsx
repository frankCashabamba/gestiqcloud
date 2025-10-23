import React, { Suspense, useEffect, useMemo, useState } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import { useI18n } from '../i18n/I18nProvider'
import { useMisModulos } from '../hooks/useMisModulos'

// Convención: cada módulo expone ./<modulo>/Routes.tsx (preferido) o ./<modulo>/Panel.tsx
// Ejemplos: contabilidad/Panel.tsx, inventario/Panel.tsx, ventas/Routes.tsx, etc.

// Nota: las rutas de Vite en import.meta.glob son relativas a este archivo
const ROUTES = import.meta.glob('./*/Routes.tsx')
const PANELS = import.meta.glob('./*/Panel.tsx')

// Alias profesionales para compatibilidad (slug antiguo/inglés -> carpeta actual)
// Mantener orden alfabético por clave
const ALIASES: Record<string, string> = {
  'accounting': 'contabilidad',
  'billing': 'facturacion',
  'cashier': 'pos',
  'customers': 'clientes',
  'expenses': 'gastos',
  'facturae': 'facturacion',
  'finance': 'finanzas',
  'human-resources': 'rrhh',
  'import': 'importador',
  'imports': 'importador',
  'importar': 'importador',
  'inventory': 'inventario',
  'invoicing': 'facturacion',
  'products': 'inventario',
  'providers': 'proveedores',
  'purchases': 'compras',
  'sales': 'ventas',
  'settings': 'settings',
  'stock': 'inventario',
  'tpv': 'pos',
  'compras-proveedores': 'compras',
}

export default function ModuleLoader() {
  const { mod } = useParams()
  const [Component, setComponent] = useState<React.ComponentType<any> | null>(null)
  const { t } = useI18n()
  const { allowedSlugs, loading } = useMisModulos()

  const folder = useMemo(() => {
    if (!mod) return ''
    const norm = mod.toLowerCase()
    return ALIASES[norm] || norm
  }, [mod])
  const keyRoutes = useMemo(() => (folder ? `./${folder}/Routes.tsx` : ''), [folder])
  const keyPanel = useMemo(() => (folder ? `./${folder}/Panel.tsx` : ''), [folder])

  // Permisos: normaliza slugs permitidos aplicando ALIASES -> carpeta canónica
  const allowedCanonical = useMemo(() => {
    const set = new Set<string>()
    allowedSlugs.forEach((s) => {
      const norm = s.toLowerCase()
      set.add(ALIASES[norm] || norm)
    })
    return set
  }, [allowedSlugs])

  useEffect(() => {
    let cancelled = false
    async function load() {
      if (!mod) return
      const importer = (ROUTES as any)[keyRoutes] || (PANELS as any)[keyPanel]
      if (!importer) { setComponent(null); return }
      try {
        const modImp: any = await importer()
        if (!cancelled) setComponent(() => modImp.default || modImp)
      } catch {
        if (!cancelled) setComponent(null)
      }
    }
    load()
    return () => { cancelled = true }
  }, [mod, keyRoutes, keyPanel])

  if (!mod) return <Navigate to="/error" replace />
  // Reactiva validación de acceso: solo bloquea cuando dejó de cargar
  // y el slug del módulo no está permitido para el tenant/usuario.
  if (!loading && folder && !allowedCanonical.has(folder)) {
    // Permitir módulos administrativos que no figuran en el catálogo público
    const exempt = new Set(['usuarios'])
    if (!exempt.has(folder)) {
      return <Navigate to="/unauthorized" replace />
    }
  }
  if (!Component) return <div style={{ padding: 16 }}>{t('common:loading.module')}</div>

  return (
    <Suspense fallback={<div style={{ padding: 16 }}>{t('common:loading.module')}</div>}>
      <Component />
    </Suspense>
  )
}
