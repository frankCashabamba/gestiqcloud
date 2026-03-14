import React, { useEffect, useMemo, useState, CSSProperties } from 'react'

import { Link } from 'react-router-dom'

import { listModulos, removeModulo, toggleModulo, registrarModulosFS, type Module } from '../../services/modulos'
import { useToast, getErrorMessage } from '../../shared/toast'

const CATEGORY_ORDER = ['core', 'operations', 'finance', 'integrations', 'ai', 'admin', 'other']

function titleCase(s: string) {
  return (s || '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function categoryLabel(cat: string | null | undefined): string {
  if (!cat) return 'Otros'
  const map: Record<string, string> = {
    core: 'Negocio principal',
    operations: 'Operaciones',
    finance: 'Finanzas y contabilidad',
    integrations: 'Integraciones',
    ai: 'IA y automatización',
    admin: 'Administración',
  }
  return map[cat] || titleCase(cat)
}

function groupByCategory(modules: Module[]): { category: string; label: string; modules: Module[] }[] {
  const groups = new Map<string, Module[]>()
  for (const m of modules) {
    const cat = m.category || 'other'
    if (!groups.has(cat)) groups.set(cat, [])
    groups.get(cat)!.push(m)
  }
  return CATEGORY_ORDER
    .filter((c) => groups.has(c))
    .concat([...groups.keys()].filter((c) => !CATEGORY_ORDER.includes(c)))
    .filter((c, i, arr) => arr.indexOf(c) === i)
    .map((cat) => ({
      category: cat,
      label: categoryLabel(cat),
      modules: groups.get(cat) || [],
    }))
}

const s = {
  page: {
    padding: 'var(--gc-page-x)',
    maxWidth: 1100,
    margin: '0 auto',
  } as CSSProperties,
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 20,
  } as CSSProperties,
  title: {
    fontSize: 20,
    fontWeight: 700,
    color: 'var(--gc-foreground)',
    margin: 0,
  } as CSSProperties,
  subtitle: {
    fontSize: 13,
    color: 'var(--gc-muted)',
    marginTop: 2,
  } as CSSProperties,
  actions: {
    display: 'flex',
    gap: 8,
  } as CSSProperties,
  btnSecondary: {
    padding: '7px 14px',
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--gc-foreground)',
    background: 'var(--gc-surface)',
    border: '1px solid var(--gc-border)',
    borderRadius: 'var(--gc-radius-sm)',
    cursor: 'pointer',
  } as CSSProperties,
  btnPrimary: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '7px 14px',
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--gc-on-primary)',
    background: 'var(--gc-primary)',
    border: 'none',
    borderRadius: 'var(--gc-radius-sm)',
    cursor: 'pointer',
    textDecoration: 'none',
  } as CSSProperties,
  searchWrap: {
    position: 'relative',
    marginBottom: 24,
  } as CSSProperties,
  searchInput: {
    width: '100%',
    maxWidth: 320,
    padding: '8px 12px 8px 34px',
    fontSize: 13,
    border: '1px solid var(--gc-border)',
    borderRadius: 'var(--gc-radius-sm)',
    outline: 'none',
    background: 'var(--gc-surface)',
    color: 'var(--gc-foreground)',
  } as CSSProperties,
  searchIcon: {
    position: 'absolute',
    left: 10,
    top: '50%',
    transform: 'translateY(-50%)',
    width: 16,
    height: 16,
    color: 'var(--gc-muted)',
  } as CSSProperties,
  sectionTitle: {
    fontSize: 11,
    fontWeight: 600,
    color: 'var(--gc-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    marginBottom: 10,
  } as CSSProperties,
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
    gap: 12,
    marginBottom: 28,
  } as CSSProperties,
  card: (active: boolean): CSSProperties => ({
    position: 'relative',
    background: active ? 'var(--gc-surface)' : 'var(--gc-bg)',
    border: `1px solid ${active ? 'var(--gc-border)' : 'var(--gc-border)'}`,
    borderRadius: 'var(--gc-radius-md)',
    padding: 14,
    opacity: active ? 1 : 0.55,
    boxShadow: active ? 'var(--gc-shadow-xs)' : 'none',
    transition: 'box-shadow 0.15s, opacity 0.15s',
  }),
  dot: (active: boolean): CSSProperties => ({
    position: 'absolute',
    top: 10,
    right: 10,
    width: 8,
    height: 8,
    borderRadius: '50%',
    background: active ? 'var(--gc-success)' : '#cbd5e1',
  }),
  cardTop: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 10,
    marginBottom: 10,
  } as CSSProperties,
  iconBox: {
    width: 36,
    height: 36,
    borderRadius: 'var(--gc-radius-sm)',
    background: 'var(--gc-bg)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 18,
    flexShrink: 0,
  } as CSSProperties,
  cardName: {
    fontSize: 13,
    fontWeight: 600,
    color: 'var(--gc-foreground)',
    margin: 0,
    lineHeight: 1.3,
  } as CSSProperties,
  cardDesc: {
    fontSize: 11,
    color: 'var(--gc-muted)',
    margin: '2px 0 0',
    lineHeight: 1.4,
    overflow: 'hidden',
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
  } as CSSProperties,
  cardActions: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    paddingTop: 10,
    borderTop: '1px solid var(--gc-border)',
  } as CSSProperties,
  actionLink: (color: string): CSSProperties => ({
    fontSize: 11,
    fontWeight: 500,
    color,
    background: 'none',
    border: 'none',
    padding: 0,
    cursor: 'pointer',
    textDecoration: 'none',
  }),
  separator: {
    color: 'var(--gc-border)',
    fontSize: 11,
    userSelect: 'none',
  } as CSSProperties,
  badge: {
    fontSize: 10,
    fontWeight: 500,
    background: '#fef3c7',
    color: '#92400e',
    padding: '2px 8px',
    borderRadius: 'var(--gc-radius-full)',
    marginBottom: 8,
    display: 'inline-block',
  } as CSSProperties,
  empty: {
    textAlign: 'center',
    padding: '48px 0',
    color: 'var(--gc-muted)',
    fontSize: 14,
  } as CSSProperties,
  footer: {
    paddingTop: 16,
    borderTop: '1px solid var(--gc-border)',
  } as CSSProperties,
}

export default function ModuleManagement() {
  const [modulos, setModulos] = useState<Module[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [blockedIds, setBlockedIds] = useState<Set<string>>(new Set())

  const { success, error: toastError } = useToast()

  useEffect(() => {
    ;(async () => {
      try {
        setLoading(true)
        const data = await listModulos()
        setModulos(data)
      } catch (e: any) {
        const m = getErrorMessage(e)
        setError(m)
        toastError(m)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const filtered = useMemo(() => {
    if (!search.trim()) return modulos
    const q = search.toLowerCase()
    return modulos.filter(
      (m) =>
        m.name.toLowerCase().includes(q) ||
        (m.description || '').toLowerCase().includes(q) ||
        (m.category || '').toLowerCase().includes(q),
    )
  }, [modulos, search])

  const groups = useMemo(() => groupByCategory(filtered), [filtered])
  const activeCount = modulos.filter((m) => m.active).length

  const handleToggle = async (m: Module) => {
    try {
      const res = await toggleModulo(m.id, !m.active)
      setModulos((prev) => prev.map((x) => (x.id === m.id ? { ...x, active: res.active } : x)))
      success(res.active ? 'Módulo activado' : 'Módulo desactivado')
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  const handleDelete = async (m: Module) => {
    if (!confirm(`¿Eliminar el módulo "${titleCase(m.name)}"?`)) return
    try {
      await removeModulo(m.id)
      setModulos((prev) => prev.filter((x) => x.id !== m.id))
      setBlockedIds((prev) => { const next = new Set(prev); next.delete(String(m.id)); return next })
      success('Módulo eliminado')
    } catch (e: any) {
      const status = e?.response?.status
      if (status === 404) {
        setModulos((prev) => prev.filter((x) => x.id !== m.id))
        toastError('El módulo ya no existe; se removió del listado')
      } else if (status === 409) {
        if (!confirm('Módulo asignado a tenants. ¿Desasignar y eliminar?')) {
          setBlockedIds((prev) => new Set(prev).add(String(m.id)))
          return
        }
        try {
          await removeModulo(m.id, { force: true })
          setModulos((prev) => prev.filter((x) => x.id !== m.id))
          setBlockedIds((prev) => { const next = new Set(prev); next.delete(String(m.id)); return next })
          success('Desasignado y eliminado')
        } catch (inner: any) {
          toastError(getErrorMessage(inner))
        }
      } else {
        toastError(getErrorMessage(e))
      }
    }
  }

  return (
    <div style={s.page}>
      {/* Header */}
      <div style={s.header}>
        <div>
          <h1 style={s.title}>Gestión de Módulos</h1>
          <p style={s.subtitle}>{modulos.length} módulos · {activeCount} activos</p>
        </div>
        <div style={s.actions}>
          <button
            style={s.btnSecondary}
            onClick={async () => {
              try {
                setLoading(true)
                const res = await registrarModulosFS()
                const data = await listModulos()
                setModulos(data)
                success(`Sincronizado: ${res.registered?.length || 0} nuevos, ${res.already_existing?.length || 0} existentes`)
              } catch (e: any) {
                toastError(getErrorMessage(e))
              } finally {
                setLoading(false)
              }
            }}
          >
            ⟳ Sincronizar
          </button>
          <Link to="crear" style={s.btnPrimary}>+ Crear módulo</Link>
        </div>
      </div>

      {/* Search */}
      <div style={s.searchWrap}>
        <svg style={s.searchIcon as any} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          type="text"
          placeholder="Buscar módulos…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={s.searchInput}
        />
      </div>

      {loading && <p style={{ fontSize: 13, color: 'var(--gc-muted)' }}>Cargando…</p>}
      {error && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', padding: '10px 14px', borderRadius: 'var(--gc-radius-sm)', fontSize: 13, marginBottom: 16 }}>
          {error}
        </div>
      )}

      {/* Groups */}
      {groups.map((group) => (
        <div key={group.category}>
          <p style={s.sectionTitle}>{group.label}</p>
          <div style={s.grid}>
            {group.modules.map((m) => (
              <div
                key={m.id}
                style={s.card(m.active)}
                onMouseEnter={(e) => { if (m.active) (e.currentTarget.style.boxShadow = 'var(--gc-shadow-sm)') }}
                onMouseLeave={(e) => { e.currentTarget.style.boxShadow = m.active ? 'var(--gc-shadow-xs)' : 'none' }}
              >
                <div style={s.dot(m.active)} title={m.active ? 'Activo' : 'Inactivo'} />

                <div style={s.cardTop}>
                  <div style={s.iconBox}>{m.icon || '🧩'}</div>
                  <div style={{ minWidth: 0, flex: 1, paddingRight: 14 }}>
                    <p style={s.cardName}>{titleCase(m.name)}</p>
                    {m.description && <p style={s.cardDesc}>{m.description}</p>}
                  </div>
                </div>

                {blockedIds.has(String(m.id)) && (
                  <span style={s.badge}>Asignado a tenants</span>
                )}

                <div style={s.cardActions}>
                  <Link to={`editar/${m.id}`} style={s.actionLink('var(--gc-primary)')}>Editar</Link>
                  <span style={s.separator}>·</span>
                  <button
                    onClick={() => handleToggle(m)}
                    style={s.actionLink(m.active ? 'var(--gc-warning)' : 'var(--gc-success)')}
                  >
                    {m.active ? 'Desactivar' : 'Activar'}
                  </button>
                  <span style={s.separator}>·</span>
                  <button onClick={() => handleDelete(m)} style={s.actionLink('var(--gc-danger)')}>
                    Eliminar
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {!loading && filtered.length === 0 && (
        <div style={s.empty as any}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>🔍</div>
          <p>No se encontraron módulos</p>
        </div>
      )}

      <div style={s.footer}>
        <Link to="asignaciones" style={{ fontSize: 13, fontWeight: 500, color: 'var(--gc-primary)' }}>
          Ver asignaciones de módulos →
        </Link>
      </div>
    </div>
  )
}
