import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listGastos, removeGasto, getGastoStats, type Gasto, type GastoStats } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import StatusBadge from '../ventas/components/StatusBadge'
import StatsCard from './components/StatsCard'

export default function GastosList() {
  const [items, setItems] = useState<Gasto[]>([])
  const [stats, setStats] = useState<GastoStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  const [categoria, setCategoria] = useState('')
  const [estado, setEstado] = useState('')
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [q, setQ] = useState('')
  const [sortKey, setSortKey] = useState<'fecha' | 'monto' | 'categoria' | 'estado'>('fecha')
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
    if (categoria && v.categoria !== categoria) return false
    if (estado && v.estado !== estado) return false
    if (desde && v.fecha < desde) return false
    if (hasta && v.fecha > hasta) return false
    if (q) {
      const search = q.toLowerCase()
      const matches =
        String(v.id).includes(search) ||
        v.concepto.toLowerCase().includes(search) ||
        v.categoria.toLowerCase().includes(search) ||
        (v.proveedor_nombre || '').toLowerCase().includes(search) ||
        (v.factura_numero || '').toLowerCase().includes(search)
      if (!matches) return false
    }
    return true
  }), [items, categoria, estado, desde, hasta, q])

  const sorted = useMemo(() => {
    const dir = sortDir === 'asc' ? 1 : -1
    return [...filtered].sort((a, b) => {
      const av = (a as any)[sortKey] || ''
      const bv = (b as any)[sortKey] || ''
      if (sortKey === 'monto') return ((av as number) - (bv as number)) * dir
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
    const header = ['id', 'fecha', 'categoria', 'concepto', 'monto', 'estado', 'proveedor']
    const body = rows.map(r => [
      r.id,
      r.fecha,
      r.categoria,
      r.concepto,
      r.monto,
      r.estado,
      r.proveedor_nombre || ''
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

  const categorias = Array.from(new Set(items.map(g => g.categoria))).sort()

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="font-semibold text-lg">Gastos</h2>
        <div className="flex gap-2">
          <button
            className="bg-gray-200 px-3 py-1 rounded hover:bg-gray-300"
            onClick={() => exportCSV(view)}
          >
            Exportar CSV
          </button>
          <button
            className="bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700"
            onClick={() => nav('nuevo')}
          >
            Nuevo Gasto
          </button>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <StatsCard
            title="Total Período"
            value={`$${stats.total_periodo.toFixed(2)}`}
            color="blue"
          />
          <StatsCard
            title="Pendiente de Pago"
            value={`$${stats.pendiente_pago.toFixed(2)}`}
            color="red"
          />
          {stats.por_categoria.slice(0, 2).map((cat) => (
            <StatsCard
              key={cat.categoria}
              title={cat.categoria}
              value={`$${cat.total.toFixed(2)}`}
              color="gray"
            />
          ))}
        </div>
      )}

      <div className="mb-3 flex flex-wrap items-end gap-3">
        <div>
          <label className="text-sm mr-2">Categoría</label>
          <select
            value={categoria}
            onChange={(e) => setCategoria(e.target.value)}
            className="border px-2 py-1 rounded text-sm"
          >
            <option value="">Todas</option>
            {categorias.map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-sm mr-2">Estado</label>
          <select
            value={estado}
            onChange={(e) => setEstado(e.target.value)}
            className="border px-2 py-1 rounded text-sm"
          >
            <option value="">Todos</option>
            <option value="pendiente">Pendiente</option>
            <option value="pagado">Pagado</option>
            <option value="anulado">Anulado</option>
          </select>
        </div>
        <div>
          <label className="text-sm mr-2">Desde</label>
          <input
            type="date"
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
            className="border px-2 py-1 rounded text-sm"
          />
        </div>
        <div>
          <label className="text-sm mr-2">Hasta</label>
          <input
            type="date"
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
            className="border px-2 py-1 rounded text-sm"
          />
        </div>
        <div>
          <label className="text-sm mr-2">Buscar</label>
          <input
            placeholder="Concepto, proveedor..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="border px-2 py-1 rounded text-sm"
          />
        </div>
      </div>

      {loading && <div className="text-sm text-gray-500">Cargando…</div>}
      {errMsg && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{errMsg}</div>}

      <div className="flex items-center gap-3 mb-2 text-sm">
        <label>Por página</label>
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
                  Fecha {sortKey === 'fecha' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </button>
              </th>
              <th className="py-2 px-2">
                <button className="underline" onClick={() => toggleSort('categoria')}>
                  Categoría {sortKey === 'categoria' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </button>
              </th>
              <th className="py-2 px-2">Concepto</th>
              <th className="py-2 px-2">
                <button className="underline" onClick={() => toggleSort('monto')}>
                  Importe {sortKey === 'monto' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </button>
              </th>
              <th className="py-2 px-2">
                <button className="underline" onClick={() => toggleSort('estado')}>
                  Estado {sortKey === 'estado' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </button>
              </th>
              <th className="py-2 px-2">Proveedor</th>
              <th className="py-2 px-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {view.map((v) => (
              <tr key={v.id} className="border-b hover:bg-gray-50">
                <td className="py-2 px-2">{v.fecha}</td>
                <td className="py-2 px-2">
                  <span className="bg-gray-100 px-2 py-1 rounded text-xs">
                    {v.categoria}
                  </span>
                </td>
                <td className="py-2 px-2">{v.concepto}</td>
                <td className="py-2 px-2 font-medium">${v.monto.toFixed(2)}</td>
                <td className="py-2 px-2">
                  <StatusBadge estado={v.estado} />
                </td>
                <td className="py-2 px-2">{v.proveedor_nombre || '-'}</td>
                <td className="py-2 px-2">
                  <Link to={`${v.id}/editar`} className="text-blue-600 hover:underline mr-3">
                    Editar
                  </Link>
                  {v.estado === 'pendiente' && (
                    <button
                      className="text-red-700 hover:underline"
                      onClick={async () => {
                        if (!confirm('¿Eliminar gasto?')) return
                        try {
                          await removeGasto(v.id)
                          setItems((p) => p.filter(x => x.id !== v.id))
                          success('Gasto eliminado')
                        } catch (e: any) {
                          toastError(getErrorMessage(e))
                        }
                      }}
                    >
                      Eliminar
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {!loading && view.length === 0 && (
              <tr>
                <td className="py-3 px-3 text-center text-gray-500" colSpan={7}>
                  Sin registros
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
