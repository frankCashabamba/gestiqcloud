import { useEffect, useMemo, useState } from 'react'
import { listMisModulos, listModulosSeleccionablesPorEmpresa, type Modulo } from '../services/modules'
import { useParams } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import i18n from '../i18n'
import { canonicalizeCompanyModuleKey } from '../lib/companyModuleKeys'

function toSlug(m: Modulo): string {
  if (m.slug) return canonicalizeCompanyModuleKey(m.slug)
  if (m.url) {
    const u = m.url.trim()
    const s = u.startsWith('/') ? u.slice(1) : u
    const seg = s.split('/')[0] || s
    return canonicalizeCompanyModuleKey(seg)
  }
  return canonicalizeCompanyModuleKey(m.name || '')
}

const MODULE_NAME_KEYS: Record<string, string> = {
  dashboard: 'nav.dashboard',
  sales: 'nav.sales',
  products: 'nav.products',
  customers: 'nav.clients',
  suppliers: 'nav.suppliers',
  inventory: 'nav.inventory',
  invoicing: 'nav.invoicing',
  reports: 'nav.reports',
  settings: 'nav.settings',
  users: 'nav.users',
  pos: 'nav.pos',
  accounting: 'modules.accounting',
  purchases: 'modules.purchases',
  expenses: 'modules.expenses',
  hr: 'modules.hr',
  imports: 'modules.importer',
  manufacturing: 'modules.manufacturing',
  finance: 'modules.finances',
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

        const modsWithItems = mods as unknown as { items?: Modulo[] }
        const list = Array.isArray(mods)
          ? mods
          : (modsWithItems && Array.isArray(modsWithItems.items))
          ? (modsWithItems.items as Modulo[])
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

  const routedSlugs = useMemo(() => {
    const list = Array.isArray(modules) ? modules : []
    return new Set(
      list
        .filter((m) => m.active !== false && m.use_module_loader !== false)
        .map(toSlug),
    )
  }, [modules])

  const sidebarModules = useMemo(
    () => modules.filter((m) => (m.nav_group || 'sidebar') === 'sidebar'),
    [modules],
  )

  const backofficeModules = useMemo(
    () => modules.filter((m) => m.nav_group === 'backoffice'),
    [modules],
  )

  const userMenuModules = useMemo(
    () => modules.filter((m) => m.nav_group === 'user_menu'),
    [modules],
  )

  const visibleModules = useMemo(
    () => modules.filter((m) => (m.nav_group || 'sidebar') !== 'hidden'),
    [modules],
  )

  return {
    modules,
    visibleModules,
    sidebarModules,
    backofficeModules,
    userMenuModules,
    allowedSlugs,
    routedSlugs,
    loading,
    error,
  }
}
