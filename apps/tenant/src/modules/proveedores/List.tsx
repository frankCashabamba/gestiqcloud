import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listProveedores, removeProveedor, type Proveedor } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'

export default function ProveedoresList() {
  const [items, setItems] = useState<Proveedor[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const [filterActivo, setFilterActivo] = useState<'all' | 'active' | 'inactive'>('active')
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        setLoading(true)
        const data = await listProveedores()
        if (cancelled) return
        setItems(data)
      } catch (e: any) {
        if (cancelled) return
        const m = getErrorMessage(e)
        setErrMsg(m)
        toastError(m)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const filtered = useMemo(() => {
    let result = items

    // Filtro activo/inactivo
    if (filterActivo === 'active') {
      result = result.filter((p) => p.active !== false)
    } else if (filterActivo === 'inactive') {
      result = result.filter((p) => p.active === false)
    }

    // Búsqueda por texto
    const term = q.toLowerCase()
    if (term) {
      result = result.filter((p) => {
        const nombre = (p.name || '').toLowerCase()
        const nombreComercial = (p.nombre_comercial || '').toLowerCase()
        const nif = (p.nif || '').toLowerCase()
        const email = (p.email || '').toLowerCase()
        return (
          nombre.includes(term) ||
          nombreComercial.includes(term) ||
          nif.includes(term) ||
          email.includes(term)
        )
      })
    }

    return result
  }, [items, q, filterActivo])

  const { page, setPage, totalPages, view } = usePagination(filtered, 15)

  const handleRemove = async (id: number | string) => {
    if (!confirm('¿Desactivar este proveedor?')) return
    try {
      await removeProveedor(id)
      setItems((prev) => prev.filter((p) => p.id !== id))
      success('Proveedor desactivado')
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Proveedores</h2>
          <p className="text-sm text-slate-500">
            Gestiona tu red de proveedores, contactos y direcciones de envío.
          </p>
        </div>
        <button className="gc-button gc-button--primary" onClick={() => nav('nuevo')}>
          + Nuevo Proveedor
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar por nombre, NIF, email..."
          className="w-full max-w-md rounded-xl border border-slate-200 px-4 py-2 text-sm"
        />
        <select
          value={filterActivo}
          onChange={(e) => setFilterActivo(e.target.value as any)}
          className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
        >
          <option value="all">Todos</option>
          <option value="active">Activos</option>
          <option value="inactive">Inactivos</option>
        </select>
      </div>

      {loading && <div className="text-sm text-slate-500">Cargando proveedores…</div>}
      {errMsg && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-sm text-rose-700">
          {errMsg}
        </div>
      )}

      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Código</th>
              <th className="px-4 py-3">Nombre / Razón Social</th>
              <th className="px-4 py-3">NIF / Tax ID</th>
              <th className="px-4 py-3">Email</th>
              <th className="px-4 py-3">Teléfono</th>
              <th className="px-4 py-3">País</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {view.map((p) => (
              <tr key={p.id} className="border-t border-slate-100 hover:bg-slate-50">
                <td className="px-4 py-3 font-mono text-xs text-slate-600">
                  PRV-{String(p.id).padStart(5, '0')}
                </td>
                <td className="px-4 py-3">
                  <Link
                    to={`${p.id}`}
                    className="font-medium text-blue-600 hover:text-blue-500 hover:underline"
                  >
                    {p.name}
                  </Link>
                  {p.nombre_comercial && (
                    <div className="text-xs text-slate-500">{p.nombre_comercial}</div>
                  )}
                </td>
                <td className="px-4 py-3 text-slate-600">{p.nif || '—'}</td>
                <td className="px-4 py-3 text-slate-600">{p.email || '—'}</td>
                <td className="px-4 py-3 text-slate-600">{p.phone || '—'}</td>
                <td className="px-4 py-3 text-slate-600">{p.pais || '—'}</td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
                      p.active !== false
                        ? 'bg-emerald-50 text-emerald-700'
                        : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {p.active !== false ? 'Activo' : 'Inactivo'}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex flex-wrap items-center justify-end gap-3">
                    <Link
                      to={`${p.id}/editar`}
                      className="text-sm font-medium text-blue-600 hover:text-blue-500"
                    >
                      Editar
                    </Link>
                    <button
                      className="text-sm font-medium text-rose-600 hover:text-rose-500"
                      onClick={() => handleRemove(p.id)}
                    >
                      Desactivar
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!loading && view.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-sm text-slate-500" colSpan={8}>
                  No se encontraron proveedores con ese filtro.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Pagination page={page} setPage={setPage} totalPages={totalPages} />
    </div>
  )
}
