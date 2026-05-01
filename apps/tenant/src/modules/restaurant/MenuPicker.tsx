import React, { useEffect, useMemo, useState } from 'react'
import { listMenu, MenuItem } from './services'

export interface MenuPickerProps {
  onPick: (item: MenuItem) => void
  search?: string
  limit?: number
}

/**
 * MenuPicker: lee `/tenant/restaurant/menu` (productos vendibles, no raw_material)
 * y muestra una lista filtrable por nombre/categoría.
 */
export default function MenuPicker({ onPick, search = '', limit = 24 }: MenuPickerProps) {
  const [items, setItems] = useState<MenuItem[]>([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let cancel = false
    listMenu()
      .then((data) => {
        if (!cancel) setItems(data)
      })
      .catch(() => {
        if (!cancel) setErr('No se pudo cargar el menú')
      })
      .finally(() => {
        if (!cancel) setLoading(false)
      })
    return () => {
      cancel = true
    }
  }, [])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    const list = q
      ? items.filter(
          (p) =>
            p.name.toLowerCase().includes(q) ||
            (p.category ?? '').toLowerCase().includes(q),
        )
      : items
    return list.slice(0, limit)
  }, [items, search, limit])

  if (loading) return <div className="text-sm text-slate-500">Cargando menú…</div>
  if (err) return <div className="text-sm text-red-600">{err}</div>
  if (filtered.length === 0)
    return <div className="text-sm text-slate-400">Sin productos disponibles</div>

  return (
    <ul className="space-y-1 max-h-96 overflow-y-auto" data-testid="menu-picker">
      {filtered.map((p) => (
        <li key={p.id}>
          <button
            onClick={() => onPick(p)}
            className="w-full text-left p-2 rounded hover:bg-blue-50 border flex justify-between items-center"
          >
            <span className="truncate">
              {p.name}
              {p.category && (
                <span className="ml-2 text-xs text-slate-500">· {p.category}</span>
              )}
            </span>
            <span className="text-sm font-mono">${p.price.toFixed(2)}</span>
          </button>
        </li>
      ))}
    </ul>
  )
}
