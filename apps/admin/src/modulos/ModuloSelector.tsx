import { useModulos } from './useModulos'

interface Props {
  selected: number[]
  onChange: (moduloId: number) => void
  showTitle?: boolean
}

export default function ModuloSelector({ selected, onChange, showTitle = false }: Props) {
  const { modulos, loading, error } = useModulos()

  const toggleModulo = (id: number) => onChange(id)

  return (
    <section>
      {showTitle && <h2 className="text-lg font-semibold text-slate-900 mb-4">Módulos a contratar</h2>}
      {loading && <div className="mb-3 text-sm text-slate-500">Cargando módulos…</div>}
      {error && (
        <div className="mb-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-sm text-rose-700">{error}</div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {modulos.map((m) => {
          const checked = selected.includes(m.id)
          return (
            <label
              key={m.id}
              className={`group relative flex items-start gap-3 rounded-2xl border p-4 shadow-sm transition hover:shadow-md cursor-pointer ${
                checked ? 'border-indigo-300 bg-indigo-50/40' : 'border-slate-200 bg-white'
              }`}
            >
              <div className={`flex h-10 w-10 items-center justify-center rounded-xl text-lg ${checked ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600'}`}>
                <span aria-hidden>{m.icono || '🧩'}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <p className="truncate text-sm font-semibold text-slate-900">{m.nombre}</p>
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-indigo-600"
                    checked={checked}
                    onChange={() => toggleModulo(m.id)}
                  />
                </div>
                <p className="mt-1 text-xs text-slate-500">{m.descripcion || `Activar acceso al módulo ${m.nombre.toLowerCase()}.`}</p>
              </div>
            </label>
          )
        })}
      </div>
    </section>
  )
}

