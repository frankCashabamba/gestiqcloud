import { useMemo } from 'react'
import { useModulos } from './useModulos'

interface Props {
  selected: string[]
  onChange: (moduloId: string) => void
  showTitle?: boolean
}

function titleCase(s: string) {
  const t = (s || '').trim()
  if (!t) return ''
  return t.charAt(0).toUpperCase() + t.slice(1)
}

const NAME_MAP: Record<string, string> = {
  rrhh: 'HR',
  recursos_humanos: 'HR',
  importador: 'Importer',
  finanzas: 'Finance',
  proveedores: 'Suppliers',
  gastos: 'Expenses',
  inventario: 'Inventory',
}

function formatNombre(raw: string) {
  const key = (raw || '').trim().toLowerCase().replace(/\s+/g, '_')
  return NAME_MAP[key] || titleCase(raw)
}

export default function ModuloSelector({ selected, onChange, showTitle = false }: Props) {
  const { modulos, loading, error } = useModulos()

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

  const hasItems = items.length > 0
  const allSelected = hasItems && items.every((m) => selected.includes(m.id))

  const handleToggleAll = () => {
    if (!hasItems) return
    const ids = items.map((m) => m.id)
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

  return (
    <section>
      {(showTitle || hasItems) && (
        <div className="mb-4 flex flex-wrap items-center gap-3">
          {showTitle && (
            <h2 className="text-lg font-semibold text-slate-900">Módulos a contratar</h2>
          )}
          {hasItems && (
            <label
              className={`inline-flex items-center gap-2 text-sm font-medium text-slate-700 ${
                showTitle ? 'ml-auto' : ''
              }`}
            >
              <input
                type="checkbox"
                className="h-4 w-4 accent-indigo-600"
                checked={allSelected}
                onChange={handleToggleAll}
                aria-label={allSelected ? 'Desactivar todos los módulos' : 'Activar todos los módulos'}
              />
              <span>{allSelected ? 'Desactivar todos' : 'Activar todos'}</span>
            </label>
          )}
        </div>
      )}
      {loading && <div className="mb-3 text-sm text-slate-500">Cargando módulos…</div>}
      {error && (
        <div className="mb-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-sm text-rose-700">
          {error}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((m) => {
          const checked = selected.includes(m.id)
          return (
            <button
              key={m.id}
              type="button"
              onClick={() => onChange(m.id)}
              className={`group relative flex w-full items-start gap-3 rounded-2xl border p-4 text-left shadow-sm transition hover:shadow-md focus:outline-none focus:ring-2 focus:ring-indigo-300 ${
                checked ? 'border-indigo-300 bg-indigo-50/50' : 'border-slate-200 bg-white'
              }`}
            >
              <div
                className={`mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-lg ${
                  checked ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600'
                }`}
                aria-hidden
              >
                <span>{m.icon || '🧩'}</span>
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-3">
                  <p className="truncate text-sm font-semibold text-slate-900">{m.nombreFmt}</p>
                  <input
                    type="checkbox"
                    className="mt-0.5 h-4 w-4 accent-indigo-600"
                    checked={checked}
                    onChange={() => onChange(m.id)}
                    aria-label={`Seleccionar módulo ${m.nombreFmt}`}
                  />
                </div>
                <p className="mt-1 text-xs text-slate-500">{m.descripcionFmt}</p>
              </div>
            </button>
          )
        })}
      </div>
    </section>
  )
}
