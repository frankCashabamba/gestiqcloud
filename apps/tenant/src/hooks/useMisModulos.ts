import { useEffect, useMemo, useState } from 'react'
import { listMisModulos, listModulosSeleccionablesPorEmpresa, type Modulo } from '../services/modules'
import { useParams } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import i18n from '../i18n'

function toSlug(m: Modulo): string {
  if (m.slug) return m.slug.toLowerCase()
  if (m.url) {
    const u = m.url.trim()
    const s = u.startsWith('/') ? u.slice(1) : u
    const seg = s.split('/')[0] || s
    return seg.toLowerCase()
  }
  // fallback: normaliza nombre
  return (m.name || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, '')
}

const MODULE_NAME_KEYS: Record<string, string> = {
  // Core nav modules
  dashboard: 'nav.dashboard',
  ventas: 'nav.sales',
  sales: 'nav.sales',
  productos: 'nav.products',
  products: 'nav.products',
  clientes: 'nav.clients',
  customers: 'nav.clients',
  suppliers: 'nav.suppliers',
  proveedores: 'nav.suppliers',
  inventario: 'nav.inventory',
  inventory: 'nav.inventory',
  facturacion: 'nav.invoicing',
  invoicing: 'nav.invoicing',
  billing: 'nav.invoicing',
  reportes: 'nav.reports',
  reports: 'nav.reports',
  configuracion: 'nav.settings',
  settings: 'nav.settings',
  usuarios: 'nav.users',
  users: 'nav.users',
  pos: 'nav.pos',
  tpv: 'nav.pos',

  // Others
  contabilidad: 'modules.accounting',
  accounting: 'modules.accounting',
  compras: 'modules.purchases',
  purchases: 'modules.purchases',
  gastos: 'modules.expenses',
  expenses: 'modules.expenses',
  rrhh: 'modules.hr',
  hr: 'modules.hr',
  importer: 'modules.importer',
  imports: 'modules.importer',
  importaciones: 'modules.importer',
  produccion: 'modules.production',
  manufacturing: 'modules.production',
  finanzas: 'modules.finances',
  finance: 'modules.finances',
  finances: 'modules.finances',
  webhooks: 'modules.webhooks',
  einvoicing: 'modules.einvoicing',
  reconciliation: 'modules.reconciliation',
  templates: 'modules.templates',
}

function localizeModule(m: Modulo): Modulo {
  const slug = toSlug(m)
  const key = MODULE_NAME_KEYS[slug]
  if (!key) return { ...m, slug }
  const translated = i18n.t(key)
  if (!translated || translated === key) return { ...m, slug }
  return { ...m, slug, name: translated }
}

function dedupeModules(mods: Modulo[]): Modulo[] {
  const bySlug = new Map<string, Modulo>()
  const byId = new Map<string, Modulo>()
  for (const m of mods) {
    const id = String(m.id || '')
    if (id && !byId.has(id)) byId.set(id, m)
    const slug = toSlug(m)
    if (!slug) continue
    const existing = bySlug.get(slug)
    if (!existing) {
      bySlug.set(slug, m)
      continue
    }
    // Prefer active and entries with url when duplicates exist.
    const existingActive = existing.active !== false
    const currentActive = m.active !== false
    if (currentActive && !existingActive) {
      bySlug.set(slug, m)
      continue
    }
    if (!existing.url && m.url) {
      bySlug.set(slug, m)
    }
  }
  // Merge slug and id maps to keep any unique items without slug.
  const merged = new Map<string, Modulo>()
  for (const m of bySlug.values()) merged.set(String(m.id || toSlug(m)), m)
  for (const m of byId.values()) {
    const key = String(m.id || toSlug(m))
    if (!merged.has(key)) merged.set(key, m)
  }
  return Array.from(merged.values())
}

export function useMisModulos() {
  const [modules, setModules] = useState<Modulo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { token } = useAuth() as { token: string | null }
  const { empresa } = useParams()

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        let mods: Modulo[] = []
        if (empresa) {
          if (token) {
            // Autenticado: solo modulos asignados al usuario
            mods = await listMisModulos(token)
          } else {
            // Sin token, usamos el listado publico por empresa
            mods = await listModulosSeleccionablesPorEmpresa(empresa)
          }
        } else if (token) {
          // Autenticado por usuario (modulos asignados al usuario)
          mods = await listMisModulos(token)
        } else {
          mods = []
        }
        // Asegura siempre un array aunque el backend devuelva null/objeto
        const list = Array.isArray(mods)
          ? mods
          : (mods && Array.isArray((mods as any).items))
          ? (mods as any).items
          : []
        if (!cancelled) setModules(dedupeModules(list).map(localizeModule))
      } catch (e: any) {
        if (!cancelled) setError(e?.message || 'Error')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [token, empresa])

  const allowedSlugs = useMemo(() => {
    const list = Array.isArray(modules) ? modules : []
    return new Set(list.filter((m) => m.active !== false).map(toSlug))
  }, [modules])

  return { modules, allowedSlugs, loading, error }
}
