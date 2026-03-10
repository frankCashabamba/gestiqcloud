import { useEffect, useMemo, useState } from 'react'
import { listMisModulos, listModulosSeleccionablesPorEmpresa, type Modulo } from '../services/modules'
import { useParams } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import i18n from '../i18n'

const SLUG_CANONICAL: Record<string, string> = {
  ventas: 'sales',
  sales: 'sales',
  productos: 'products',
  products: 'products',
  clientes: 'clients',
  customers: 'clients',
  clients: 'clients',
  proveedores: 'suppliers',
  suppliers: 'suppliers',
  inventario: 'inventory',
  inventory: 'inventory',
  facturacion: 'invoicing',
  invoicing: 'invoicing',
  billing: 'invoicing',
  reportes: 'reports',
  reports: 'reports',
  configuracion: 'settings',
  settings: 'settings',
  usuarios: 'users',
  users: 'users',
  pos: 'pos',
  tpv: 'pos',
  contabilidad: 'accounting',
  accounting: 'accounting',
  compras: 'purchases',
  purchases: 'purchases',
  gastos: 'expenses',
  expenses: 'expenses',
  rrhh: 'hr',
  hr: 'hr',
  importador: 'importer',
  importer: 'importer',
  imports: 'importer',
  importaciones: 'importer',
  produccion: 'production',
  production: 'production',
  productions: 'production',
  manufacturing: 'production',
  finanzas: 'finances',
  finance: 'finances',
  finances: 'finances',
  webhooks: 'webhooks',
  reconciliation: 'reconciliation',
  conciliacion: 'reconciliation',
  conciliacionbancaria: 'reconciliation',
  templates: 'templates',
}

function normalizeSlug(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, '')
}

function canonicalizeSlug(value: string): string {
  const normalized = normalizeSlug(value)
  return SLUG_CANONICAL[normalized] || normalized
}

function toSlug(m: Modulo): string {
  if (m.slug) return canonicalizeSlug(m.slug)
  if (m.url) {
    const u = m.url.trim()
    const s = u.startsWith('/') ? u.slice(1) : u
    const seg = s.split('/')[0] || s
    return canonicalizeSlug(seg)
  }
  return canonicalizeSlug(m.name || '')
}

const MODULE_NAME_KEYS: Record<string, string> = {
  dashboard: 'nav.dashboard',
  ventas: 'nav.sales',
  sales: 'nav.sales',
  productos: 'nav.products',
  products: 'nav.products',
  clientes: 'nav.clients',
  customers: 'nav.clients',
  clients: 'nav.clients',
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

  contabilidad: 'modules.accounting',
  accounting: 'modules.accounting',
  compras: 'modules.purchases',
  purchases: 'modules.purchases',
  gastos: 'modules.expenses',
  expenses: 'modules.expenses',
  rrhh: 'modules.hr',
  hr: 'modules.hr',
  importador: 'modules.importer',
  importer: 'modules.importer',
  imports: 'modules.importer',
  importaciones: 'modules.importer',
  produccion: 'modules.manufacturing',
  production: 'modules.manufacturing',
  productions: 'modules.manufacturing',
  manufacturing: 'modules.manufacturing',
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
  for (const m of mods) {
    const slug = toSlug(m)
    if (!slug) continue
    const existing = bySlug.get(slug)
    if (!existing) {
      bySlug.set(slug, m)
      continue
    }

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

  const withoutSlug = mods.filter((m) => !toSlug(m))
  const uniqueWithoutSlug = new Map<string, Modulo>()
  for (const m of withoutSlug) {
    const key = String(m.id || '')
    if (key && !uniqueWithoutSlug.has(key)) uniqueWithoutSlug.set(key, m)
  }

  return [...bySlug.values(), ...uniqueWithoutSlug.values()]
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
      if (!cancelled) {
        setLoading(true)
        setError(null)
      }
      try {
        let mods: Modulo[] = []
        if (empresa) {
          if (token) {
            mods = await listMisModulos(token)
          } else {
            mods = await listModulosSeleccionablesPorEmpresa(empresa)
          }
        } else if (token) {
          mods = await listMisModulos(token)
        } else {
          mods = []
        }

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

    return () => {
      cancelled = true
    }
  }, [token, empresa])

  const allowedSlugs = useMemo(() => {
    const list = Array.isArray(modules) ? modules : []
    return new Set(list.filter((m) => m.active !== false).map(toSlug))
  }, [modules])

  return { modules, allowedSlugs, loading, error }
}
