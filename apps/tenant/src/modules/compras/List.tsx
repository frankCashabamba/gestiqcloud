import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listCompras, removeCompra, type Compra } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import StatusBadge from '../ventas/components/StatusBadge'

export default function ComprasList() {
  const [items, setItems] = useState<Compra[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  const [estado, setEstado] = useState('')
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [q, setQ] = useState('')
  const [sortKey, setSortKey] = useState<'fecha' | 'total' | 'estado' | 'proveedor_nombre'>('fecha')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [per, setPer] = useState(10)

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        setItems(await listCompras())
      } catch (e: any) {
        const m = getErrorMessage(e)
        setErrMsg(m)
        toastError(m)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const filtered = useMemo(() => items.filter(v => {
    if (estado && v.estado !== estado) return false
    if (desde && v.fecha < desde) return false
    if (hasta && v.fecha > hasta) return false
    if (q) {
      const search = q.toLowerCase()
      const matches =
        String(v.id).includes(search) ||
        (v.numero || '').toLowerCase().includes(search) ||
        (v.proveedor_nombre || '').toLowerCase().includes(search) ||
        v.estado.toLowerCase().includes(search)
      if (!matches) return false
    }
    return true
  }), [items, estado, desde, hasta, q])

  const sorted = useMemo(() => {
    const dir = sortDir === 'asc' ? 1 : -1
    return [...filtered].sort((a, b) => {
      const av = (a as any)[sortKey] || ''
      const bv = (b as any)[sortKey] || ''
      if (sortKey === 'total') return ((av as number) - (bv as number)) * dir
      return (av < bv ? -1 : av > bv ? 1 : 0) * dir
    })
  }, [filtered, sortKey, sortDir])

  const { page, setPage, totalPages, view, setPerPage } = usePagination(sorted, per)
  useEffect(() => setPerPage(per), [per, setPerPage])

  function exportCSV(rows: Compra[]) {
    const header = ['id', 'numero', 'fecha', 'proveedor', 'total', 'estado']
    const body = rows.map(r => [
      r.id,
      r.numero || '',
      r.fecha,
      r.proveedor_nombre || '',
      r.total,
      r.estado
    ])
    const csv = [header, ...body].map(line => line.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'compras.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const toggleSort = (key: typeof sortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-3">
        <h2 className="font-semibold text-lg">Purchases</h2>
        <div className="flex gap-2">
          <button
            className="bg-gray-200 px-3 py-1 rounded hover:bg-gray-300"
            onClick={() => exportCSV(view)}
          >
            Export CSV
          </button>
          <button
            className="bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700"
            onClick={() => nav('new')}
          >
            New Purchase
          </button>
        </div>
      </div>

      <div className="mb-3 flex flex-wrap items-end gap-3">
        <div>
          <label className="text-sm mr-2">Status</label>
          <select
            value={estado}
            onChange={(e) => setEstado(e.target.value)}
            className="border px-2 py-1 rounded text-sm"
          >
            <option value="">All</option>
            <option value="draft">Draft</option>
            <option value="sent">Sent</option>
            <option value="received">Received</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
        <div>
          <label className="text-sm mr-2">From</label>
          <input
            type="date"
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
            className="border px-2 py-1 rounded text-sm"
          />
        </div>
        <div>
          <label className="text-sm mr-2">To</label>
          <input
            type="date"
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
            className="border px-2 py-1 rounded text-sm"
          />
        </div>
        <div>
          <label className="text-sm mr-2">Search</label>
          <input
            placeholder="ID, number, supplier..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="border px-2 py-1 rounded text-sm"
          />
        </div>
      </div>

      {loading && <div className="text-sm text-gray-500">Loading…</div>}
      {errMsg && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{errMsg}</div>}

      <div className="flex items-center gap-3 mb-2 text-sm">
        <label>Per page</label>
        <select
          value={per}
          onChange={(e) => setPer(Number(e.target.value))}
          className="border px-2 py-1 rounded"
        >
          <option value={10}>10</option>
          <option value={25}>25</option>
          <option value={50}>50</option>
        </select>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left border-b">
              <th className="py-2 px-2">
                <button className="underline" onClick={() => toggleSort('fecha')}>
                  Date {sortKey === 'fecha' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </button>
              </th>
              <th className="py-2 px-2">Number</th>
              <th className="py-2 px-2">
                <button className="underline" onClick={() => toggleSort('proveedor_nombre')}>
                  Supplier {sortKey === 'proveedor_nombre' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </button>
              </th>
              <th className="py-2 px-2">
                <button className="underline" onClick={() => toggleSort('total')}>
                  Total {sortKey === 'total' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </button>
              </th>
              <th className="py-2 px-2">
                <button className="underline" onClick={() => toggleSort('estado')}>
                  Status {sortKey === 'estado' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </button>
              </th>
              <th className="py-2 px-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {view.map((v) => (
              <tr key={v.id} className="border-b hover:bg-gray-50">
                <td className="py-2 px-2">{v.fecha}</td>
                <td className="py-2 px-2">{v.numero || '-'}</td>
                <td className="py-2 px-2">{v.proveedor_nombre || '-'}</td>
                <td className="py-2 px-2">${v.total.toFixed(2)}</td>
                <td className="py-2 px-2">
                  <StatusBadge estado={v.estado} />
                </td>
                <td className="py-2 px-2">
                  <Link to={`${v.id}`} className="text-blue-600 hover:underline mr-3">
                    View
                  </Link>
                  {v.estado === 'draft' && (
                    <Link to={`${v.id}/edit`} className="text-blue-600 hover:underline mr-3">
                      Edit
                    </Link>
                  )}
                  {v.estado === 'draft' && (
                    <button
                      className="text-red-700 hover:underline"
                      onClick={async () => {
                        if (!confirm('Delete purchase?')) return
                        try {
                          await removeCompra(v.id)
                          setItems((p) => p.filter(x => x.id !== v.id))
                          success('Purchase deleted')
                        } catch (e: any) {
                          toastError(getErrorMessage(e))
                        }
                      }}
                    >
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {!loading && view.length === 0 && (
              <tr>
                <td className="py-3 px-3 text-center text-gray-500" colSpan={6}>
                  No records
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
