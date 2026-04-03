import React, { useMemo, useState } from 'react'

import { useModulos } from './useModulos'

interface Props {
  selected: string[]
  onChange: (moduloId: string) => void
  showTitle?: boolean
}

function formatNombre(raw: string) {
  const value = (raw || '').trim()
  if (!value) return ''
  if (/[A-Z]/.test(value) || value.includes(' ')) return value
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

export default function ModuloSelector({ selected, onChange, showTitle = false }: Props) {
  const { modulos, loading, error } = useModulos()
  const [search, setSearch] = useState('')

  const items = useMemo(
    () =>
      modulos.map((m) => ({
        ...m,
        nombreFmt: formatNombre(m.name),
        descripcionFmt:
          m.description ||
          `Activar acceso al módulo ${formatNombre(m.name) || 'seleccionado'}.`,
      })),
    [modulos],
  )

  const filtered = useMemo(() => {
    if (!search.trim()) return items
    const q = search.toLowerCase()
    return items.filter(
      (m) =>
        m.nombreFmt.toLowerCase().includes(q) ||
        (m.descripcionFmt || '').toLowerCase().includes(q) ||
        (m.category || '').toLowerCase().includes(q),
    )
  }, [items, search])

  const hasItems = filtered.length > 0
  const allSelected = hasItems && filtered.every((m) => selected.includes(m.id))

  const handleToggleAll = () => {
    if (!hasItems) return
    const ids = filtered.map((m) => m.id)
    if (allSelected) {
      ids.forEach((id) => {
        if (selected.includes(id)) onChange(id)
      })
    } else {
      ids.forEach((id) => {
        if (!selected.includes(id)) onChange(id)
      })
    }
  }

  const styles = {
    section: { display: 'flex', flexDirection: 'column' as const, gap: '12px' },
    header: { display: 'flex', flexWrap: 'wrap' as const, gap: '12px', alignItems: 'center', justifyContent: 'space-between' as const },
    title: { fontSize: '15px', fontWeight: 600, color: '#0f172a' },
    pill: { fontSize: '12px', fontWeight: 600, color: '#475569', background: '#f1f5f9', padding: '4px 8px', borderRadius: '999px' },
    searchWrap: { position: 'relative' as const },
    search: { width: '220px', maxWidth: '100%', borderRadius: '8px', border: '1px solid #e2e8f0', padding: '8px 10px', fontSize: '13px', boxShadow: '0 1px 2px rgba(15,23,42,0.08)' },
    searchIcon: { position: 'absolute' as const, right: '10px', top: '7px', color: '#94a3b8', pointerEvents: 'none' as const },
    toggleAll: { display: 'inline-flex', alignItems: 'center', gap: '8px', fontSize: '12px', fontWeight: 600, color: '#334155' },
    grid: { display: 'grid', gap: '10px', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', maxHeight: '320px', overflowY: 'auto' as const, paddingRight: '4px' },
    card: (checked: boolean, disabled: boolean) => ({
      position: 'relative' as const,
      display: 'flex',
      gap: '10px',
      alignItems: 'flex-start',
      width: '100%',
      borderRadius: '12px',
      border: `1px solid ${checked ? '#c7d2fe' : '#e2e8f0'}`,
      background: checked ? '#f8fafc' : '#fff',
      padding: '10px',
      textAlign: 'left' as const,
      boxShadow: '0 1px 3px rgba(15,23,42,0.06)',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.65 : 1,
      transition: 'all 150ms ease',
    }),
    icon: (checked: boolean) => ({
      height: '34px',
      width: '34px',
      borderRadius: '10px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '16px',
      background: checked ? '#e0e7ff' : '#f1f5f9',
      color: checked ? '#4338ca' : '#475569',
      flexShrink: 0,
      marginTop: '1px',
    }),
    name: { fontSize: '13px', fontWeight: 700, color: '#0f172a', lineHeight: 1.2, margin: 0 },
    desc: { fontSize: '11px', color: '#64748b', marginTop: '3px', marginBottom: 0, lineHeight: 1.35 },
    checkbox: { marginTop: '2px' },
    empty: { gridColumn: '1 / -1', border: '1px dashed #e2e8f0', background: '#f8fafc', borderRadius: '12px', padding: '20px', textAlign: 'center' as const, color: '#64748b', fontSize: '12px' },
  }

  return (
    <section style={styles.section}>
      {(showTitle || hasItems) && (
        <div style={styles.header}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' as const }}>
            {showTitle && <h2 style={styles.title}>Módulos a contratar</h2>}
            {hasItems && <span style={styles.pill}>{filtered.length} módulos</span>}
          </div>
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' as const, alignItems: 'center' }}>
            <div style={styles.searchWrap}>
              <input
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar módulo o descripción"
                style={styles.search}
              />
              <span style={styles.searchIcon}>🔍</span>
            </div>
            {hasItems && (
              <label style={styles.toggleAll}>
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={handleToggleAll}
                  aria-label={allSelected ? 'Desactivar todos los módulos' : 'Activar todos los módulos'}
                />
                <span>{allSelected ? 'Desactivar visibles' : 'Activar visibles'}</span>
              </label>
            )}
          </div>
        </div>
      )}

      {loading && <div style={{ fontSize: '13px', color: '#64748b' }}>Cargando módulos…</div>}
      {error && (
        <div style={{ border: '1px solid #fecdd3', background: '#fff1f2', color: '#be123c', padding: '10px 12px', borderRadius: '10px', fontSize: '13px' }}>
          {error}
        </div>
      )}

      <div style={styles.grid}>
        {filtered.map((m) => {
          const checked = selected.includes(m.id)
          const disabled = false
          return (
            <button
              key={m.id}
              type="button"
              onClick={() => onChange(m.id)}
              style={styles.card(checked, disabled)}
            >
              <div style={styles.icon(checked)} aria-hidden>
                <span>{m.icon || '🧩'}</span>
              </div>
              <div style={{ minWidth: 0, flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '10px' }}>
                  <p style={styles.name}>{m.nombreFmt}</p>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => onChange(m.id)}
                    aria-label={`Seleccionar módulo ${m.nombreFmt}`}
                    style={styles.checkbox}
                  />
                </div>
                <p style={styles.desc}>{m.descripcionFmt}</p>
              </div>
            </button>
          )
        })}
        {!loading && filtered.length === 0 && (
          <div style={styles.empty}>No hay módulos que coincidan con tu búsqueda.</div>
        )}
      </div>
    </section>
  )
}
