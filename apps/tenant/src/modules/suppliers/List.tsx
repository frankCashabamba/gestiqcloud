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
    if (!confirm('Deactivate this supplier?')) return
    try {
      await removeProveedor(id)
      setItems((prev) => prev.filter((p) => p.id !== id))
      success('Supplier deactivated')
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Suppliers</h2>
          <p className="text-sm text-slate-500">
            Manage your supplier network, contacts and shipping addresses.
          </p>
        </div>
        <button className="gc-button gc-button--primary" onClick={() => nav('nuevo')}>
          + New Supplier
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search by name, NIF, email..."
          className="w-full max-w-md rounded-xl border border-slate-200 px-4 py-2 text-sm"
        />
        <select
          value={filterActivo}
          onChange={(e) => setFilterActivo(e.target.value as any)}
          className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
        >
          <option value="all">All</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </div>

      {loading && <div className="text-sm text-slate-500">Loading suppliers…</div>}
      {errMsg && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-sm text-rose-700">
          {errMsg}
        </div>
      )}

      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Code</th>
              <th className="px-4 py-3">Name / Legal Name</th>
              <th className="px-4 py-3">NIF / Tax ID</th>
              <th className="px-4 py-3">Email</th>
              <th className="px-4 py-3">Phone</th>
              <th className="px-4 py-3">Country</th>
              <th className="px-4 py-3">Status</th>
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
                    {p.active !== false ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex flex-wrap items-center justify-end gap-3">
                    <Link
                      to={`${p.id}/editar`}
                      className="text-sm font-medium text-blue-600 hover:text-blue-500"
                    >
                      Edit
                    </Link>
                    <button
                      className="text-sm font-medium text-rose-600 hover:text-rose-500"
                      onClick={() => handleRemove(p.id)}
                    >
                      Deactivate
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!loading && view.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-sm text-slate-500" colSpan={8}>
                  No suppliers found with that filter.
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
