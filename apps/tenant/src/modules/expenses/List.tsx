import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listGastos, removeGasto, getGastoStats, type Gasto, type GastoStats } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import StatusBadge from '../sales/components/StatusBadge'
import StatsCard from './components/StatsCard'

export default function GastosList() {
  const [items, setItems] = useState<Gasto[]>([])
  const [stats, setStats] = useState<GastoStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [q, setQ] = useState('')
  const [sortKey, setSortKey] = useState<'date' | 'amount'>('date')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [per, setPer] = useState(10)

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        const [gastosData, statsData] = await Promise.all([
          listGastos(),
          getGastoStats(desde, hasta)
        ])
        setItems(gastosData)
        setStats(statsData)
      } catch (e: any) {
        const m = getErrorMessage(e)
        setErrMsg(m)
        toastError(m)
      } finally {
        setLoading(false)
      }
    })()
  }, [desde, hasta])

  const filtered = useMemo(() => items.filter(v => {
    if (desde && v.date < desde) return false
    if (hasta && v.date > hasta) return false
    if (q) {
      const search = q.toLowerCase()
      const matches =
        String(v.id).includes(search) ||
        (v.concept || '').toLowerCase().includes(search)
      if (!matches) return false
    }
    return true
  }), [items, desde, hasta, q])

  const sorted = useMemo(() => {
    const dir = sortDir === 'asc' ? 1 : -1
    return [...filtered].sort((a, b) => {
      let av, bv
      if (sortKey === 'date') {
        av = a.date || ''
        bv = b.date || ''
      } else if (sortKey === 'amount') {
        av = a.amount || 0
        bv = b.amount || 0
        return ((av as number) - (bv as number)) * dir
      } else {
        av = (a as any)[sortKey] || ''
        bv = (b as any)[sortKey] || ''
      }
      return (av < bv ? -1 : av > bv ? 1 : 0) * dir
    })
  }, [filtered, sortKey, sortDir])

  const { page, setPage, totalPages, view, setPerPage } = usePagination(sorted, per)
  useEffect(() => setPerPage(per), [per, setPerPage])

  const toggleSort = (key: typeof sortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  function exportCSV(rows: Gasto[]) {
    const header = ['id', 'date', 'concept', 'amount']
    const body = rows.map(r => [
      r.id,
      r.date,
      r.concept || '',
      r.amount
    ])
    const csv = [header, ...body].map(line => line.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'gastos.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
         <h2 className="font-semibold text-lg">Expenses</h2>
         <div className="flex gap-2">
           <button
             className="bg-gray-200 px-3 py-1 rounded hover:bg-gray-300"
             onClick={() => exportCSV(view)}
           >
             Export CSV
           </button>
           <button
             className="bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700"
             onClick={() => nav('nuevo')}
           >
             New Expense
           </button>
         </div>
       </div>

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <StatsCard
            title="Total"
            value={`$${stats.total.toFixed(2)}`}
            color="blue"
          />
          <StatsCard
            title="Pending"
            value={`$${stats.pending.toFixed(2)}`}
            color="red"
          />
        </div>
      )}

      <div className="mb-3 flex flex-wrap items-end gap-3">
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
            placeholder="Concept..."
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
                <button className="underline" onClick={() => toggleSort('date')}>
                  Date {sortKey === 'date' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </button>
              </th>
              <th className="py-2 px-2">Concept</th>
              <th className="py-2 px-2">
                <button className="underline" onClick={() => toggleSort('amount')}>
                  Amount {sortKey === 'amount' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </button>
              </th>
              <th className="py-2 px-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {view.map((v) => (
              <tr key={v.id} className="border-b hover:bg-gray-50">
                <td className="py-2 px-2">{v.date}</td>
                <td className="py-2 px-2">{v.concept || '-'}</td>
                <td className="py-2 px-2 font-medium">${v.amount.toFixed(2)}</td>
                <td className="py-2 px-2">
                  <Link to={`${v.id}/editar`} className="text-blue-600 hover:underline mr-3">
                    Edit
                  </Link>
                  <button
                    className="text-red-700 hover:underline"
                    onClick={async () => {
                      if (!confirm('Delete expense?')) return
                      try {
                        await removeGasto(v.id)
                        setItems((p) => p.filter(x => x.id !== v.id))
                        success('Expense deleted')
                      } catch (e: any) {
                        toastError(getErrorMessage(e))
                      }
                    }}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {!loading && view.length === 0 && (
              <tr>
                <td className="py-3 px-3 text-center text-gray-500" colSpan={4}>
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
