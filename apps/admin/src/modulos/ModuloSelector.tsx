import { useMemo } from 'react'
import { useModulos } from './useModulos'

interface Props {
  selected: number[]
  onChange: (moduloId: number) => void
  showTitle?: boolean
}

function titleCase(s: string) {
  const t = (s || '').trim()
  if (!t) return ''
  return t.charAt(0).toUpperCase() + t.slice(1)
}

const NAME_MAP: Record<string, string> = {
  rrhh: 'RR. HH.',
  recursos_humanos: 'RR. HH.',
  importador: 'Importador',
  finanzas: 'Finanzas',
  proveedores: 'Proveedores',
  gastos: 'Gastos',
  inventario: 'Inventario',
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
        nombreFmt: formatNombre(m.nombre),
        descripcionFmt: m.descripcion || `Activar acceso al módulo ${formatNombre(m.nombre)}.`,
      })),
    [modulos],
  )

  return (
    <section>
      {showTitle && (
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Módulos a contratar</h2>
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
                <span>{m.icono || '🧩'}</span>
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
