import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listProveedores, removeProveedor, type Proveedor } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'

const sortKeys = [
  { key: 'nombre', label: 'Nombre legal' },
  { key: 'nombre_comercial', label: 'Nombre comercial' },
  { key: 'nif', label: 'NIF/CIF' },
] as const

const SORT_KEY_DEFAULT = 'nombre'

type SortKey = 'nombre' | 'nombre_comercial' | 'nif'

const ARROW_ASC = '?'
const ARROW_DESC = '?'

function formatPais(value?: string | null) {
  if (!value) return '-'
  return value.toUpperCase()
}

function formatMetodoPago(value?: string | null) {
  if (!value) return '-'
  return value.replace(/_/g, ' ')
}

export default function ProveedoresList() {
  const [items, setItems] = useState<Proveedor[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
  const [q, setQ] = useState('')

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        const data = await listProveedores()
        setItems(data)
      } catch (e: any) {
        const m = getErrorMessage(e)
        setErrMsg(m)
        toastError(m)
      } finally {
        setLoading(false)
      }
    })()
  }, [toastError])

  const [sortKey, setSortKey] = useState<SortKey>(SORT_KEY_DEFAULT)
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [per, setPer] = useState(10)

  const filtered = useMemo(() => {
    const query = q.trim().toLowerCase()
    if (!query) return items
    return items.filter((p) => {
      const campos = [
        p.nombre,
        p.nombre_comercial || '',
        p.nif || '',
        p.email || '',
        p.telefono || '',
      ]
      return campos.some((value) => value.toLowerCase().includes(query))
    })
  }, [items, q])

  const sorted = useMemo(() => {
    const dir = sortDir === 'asc' ? 1 : -1
    return [...filtered].sort((a, b) => {
      const av = ((a as any)[sortKey] || '').toString().toLowerCase()
      const bv = ((b as any)[sortKey] || '').toString().toLowerCase()
      if (av < bv) return -1 * dir
      if (av > bv) return 1 * dir
      return 0
    })
  }, [filtered, sortKey, sortDir])

  const { page, setPage, totalPages, view, setPerPage } = usePagination(sorted, per)
  useEffect(() => setPerPage(per), [per, setPerPage])

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  return (
    <div className="p-4">
      <div className="flex flex-wrap justify-between items-center gap-2 mb-4">
        <h2 className="font-semibold text-lg text-slate-800">Proveedores</h2>
        <button
          className="gc-button gc-button--primary"
          onClick={() => nav('nuevo')}
        >
          Nuevo proveedor
        </button>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-4">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar por nombre, NIF, email o teléfono"
          className="w-full sm:max-w-sm px-3 py-2 border border-slate-200 rounded-lg text-sm"
        />
        <label className="text-sm text-slate-600 flex items-center gap-2">
          Por página
          <select
            value={per}
            onChange={(e) => setPer(Number(e.target.value))}
            className="border border-slate-200 rounded px-2 py-1"
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
        </label>
      </div>

      {loading && <div className="text-sm text-slate-500">Cargando proveedores…</div>}
      {errMsg && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 mb-4">
          {errMsg}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left border-b border-slate-200 bg-slate-50">
              {sortKeys.map(({ key, label }) => (
                <th key={key} className="px-3 py-2">
                  <button
                    type="button"
                    className="flex items-center gap-1 font-medium text-slate-600 hover:text-slate-900"
                    onClick={() => toggleSort(key as SortKey)}
                  >
                    {label}
                    {sortKey === key ? <span>{sortDir === 'asc' ? ARROW_ASC : ARROW_DESC}</span> : null}
                  </button>
                </th>
              ))}
              <th className="px-3 py-2">País</th>
              <th className="px-3 py-2">Email</th>
              <th className="px-3 py-2">Método pago</th>
              <th className="px-3 py-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {view.map((p) => (
              <tr key={p.id} className="border-b border-slate-100">
                <td className="px-3 py-2">{p.nombre}</td>
                <td className="px-3 py-2 text-slate-600">{p.nombre_comercial || '—'}</td>
                <td className="px-3 py-2">{p.nif || '—'}</td>
                <td className="px-3 py-2">{formatPais(p.pais)}</td>
                <td className="px-3 py-2">{p.email || '—'}</td>
                <td className="px-3 py-2">{formatMetodoPago(p.metodo_pago)}</td>
                <td className="px-3 py-2 flex gap-2">
                  <Link to={`${p.id}/editar`} className="text-blue-600 hover:underline">Editar</Link>
                  <button
                    type="button"
                    className="text-red-600 hover:underline"
                    onClick={async () => {
                      if (!confirm('¿Eliminar proveedor?')) return
                      try {
                        await removeProveedor(p.id)
                        setItems((prev) => prev.filter((x) => x.id !== p.id))
                        success('Proveedor eliminado')
                      } catch (e: any) {
                        toastError(getErrorMessage(e))
                      }
                    }}
                  >
                    Eliminar
                  </button>
                </td>
              </tr>
            ))}
            {!loading && !view.length && (
              <tr>
                <td className="px-3 py-6 text-center text-slate-500" colSpan={7}>
                  No se encontraron proveedores.
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
