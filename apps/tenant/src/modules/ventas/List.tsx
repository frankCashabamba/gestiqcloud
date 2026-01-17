import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listVentas, removeVenta, type Venta } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import StatusBadge from './components/StatusBadge'
import { PAGINATION_DEFAULTS } from '../../constants/defaults'

export default function VentasList() {
    const [items, setItems] = useState<Venta[]>([])
    const [loading, setLoading] = useState(false)
    const [errMsg, setErrMsg] = useState<string | null>(null)
    const nav = useNavigate()
    const { success, error: toastError } = useToast()
    const [estado, setEstado] = useState('')
    const [desde, setDesde] = useState('')
    const [hasta, setHasta] = useState('')
    const [q, setQ] = useState('')
    const [sortKey, setSortKey] = useState<'fecha' | 'numero' | 'total' | 'estado'>('fecha')
    const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
    const [per, setPer] = useState(PAGINATION_DEFAULTS.VENTAS_PER_PAGE)

    useEffect(() => {
        (async () => {
            try { setLoading(true); setItems(await listVentas()) }
            catch (e: any) { const m = getErrorMessage(e); setErrMsg(m); toastError(m) }
            finally { setLoading(false) }
        })()
    }, [])

    const filtered = useMemo(() => items.filter(v => {
        if (estado && (v.estado || '') !== estado) return false
        if (desde && v.fecha < desde) return false
        if (hasta && v.fecha > hasta) return false
        if (q && !(
            `${v.id}`.includes(q) ||
            (v.numero || '').toLowerCase().includes(q.toLowerCase()) ||
            (v.cliente_nombre || '').toLowerCase().includes(q.toLowerCase()) ||
            (v.estado || '').toLowerCase().includes(q.toLowerCase())
        )) return false
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

    function exportCSV(rows: Venta[]) {
        const header = ['id', 'numero', 'fecha', 'cliente', 'total', 'estado']
        const body = rows.map(r => [r.id, r.numero ?? '', r.fecha, r.cliente_nombre ?? '', r.total, r.estado ?? ''])
        const csv = [header, ...body].map(line => line.join(',')).join('\n')
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `ventas-${new Date().toISOString().slice(0, 10)}.csv`
        a.click()
        URL.revokeObjectURL(url)
    }

    return (
        <div className="p-4">
            <div className="flex justify-between items-center mb-3">
                <h2 className="font-semibold text-lg">Ventas</h2>
                <div className="flex gap-2">
                    <button className="bg-gray-200 px-3 py-1 rounded" onClick={() => exportCSV(view)}>Exportar CSV</button>
                    <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={() => nav('nueva')}>Nueva</button>
                </div>
            </div>
            <div className="mb-3 flex flex-wrap items-end gap-3">
                <div>
                    <label className="text-sm mr-2 block">Estado</label>
                    <select value={estado} onChange={(e) => setEstado(e.target.value)} className="border px-2 py-1 rounded text-sm">
                        <option value="">Todos</option>
                        <option value="borrador">Borrador</option>
                        <option value="emitida">Emitida</option>
                        <option value="anulada">Anulada</option>
                    </select>
                </div>
                <div>
                    <label className="text-sm mr-2 block">Desde</label>
                    <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className="border px-2 py-1 rounded text-sm" />
                </div>
                <div>
                    <label className="text-sm mr-2 block">Hasta</label>
                    <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className="border px-2 py-1 rounded text-sm" />
                </div>
                <div>
                    <label className="text-sm mr-2 block">Buscar</label>
                    <input placeholder="Número, cliente, estado..." value={q} onChange={(e) => setQ(e.target.value)} className="border px-2 py-1 rounded text-sm" style={{ minWidth: 200 }} />
                </div>
            </div>
            {loading && <div className="text-sm text-gray-500">Cargando…</div>}
            {errMsg && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{errMsg}</div>}
            <div className="flex items-center gap-3 mb-2 text-sm">
                <label>Por página</label>
                <select value={per} onChange={(e) => setPer(Number(e.target.value))} className="border px-2 py-1 rounded">
                    <option value={10}>10</option>
                    <option value={25}>25</option>
                    <option value={50}>50</option>
                </select>
            </div>
            <table className="min-w-full text-sm">
                <thead>
                    <tr className="text-left border-b">
                        <th className="py-2"><button className="underline" onClick={() => { setSortKey('numero'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>Número {sortKey === 'numero' ? (sortDir === 'asc' ? '↑' : '↓') : ''}</button></th>
                        <th className="py-2">Cliente</th>
                        <th className="py-2"><button className="underline" onClick={() => { setSortKey('fecha'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>Fecha {sortKey === 'fecha' ? (sortDir === 'asc' ? '↑' : '↓') : ''}</button></th>
                        <th className="py-2"><button className="underline" onClick={() => { setSortKey('total'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>Total {sortKey === 'total' ? (sortDir === 'asc' ? '↑' : '↓') : ''}</button></th>
                        <th className="py-2"><button className="underline" onClick={() => { setSortKey('estado'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>Estado {sortKey === 'estado' ? (sortDir === 'asc' ? '↑' : '↓') : ''}</button></th>
                        <th className="py-2">Acciones</th>
                    </tr>
                </thead>
                <tbody>
                    {view.map((v) => (
                        <tr key={v.id} className="border-b hover:bg-gray-50">
                            <td className="py-2">{v.numero || '-'}</td>
                            <td className="py-2">{v.cliente_nombre || '-'}</td>
                            <td className="py-2">{v.fecha}</td>
                            <td className="py-2 font-semibold">${v.total.toFixed(2)}</td>
                            <td className="py-2"><StatusBadge estado={v.estado} /></td>
                            <td className="py-2">
                                <Link to={`${v.id}`} className="text-blue-600 hover:underline mr-3">Ver</Link>
                                <Link to={`${v.id}/editar`} className="text-blue-600 hover:underline mr-3">Editar</Link>
                                {v.estado === 'borrador' && (
                                    <button className="text-green-700 hover:underline mr-3" onClick={() => nav(`${v.id}/facturar`)}>Facturar</button>
                                )}
                                <button className="text-red-700 hover:underline" onClick={async () => { if (!confirm('¿Eliminar venta?')) return; try { await removeVenta(v.id); setItems((p) => p.filter(x => x.id !== v.id)); success('Venta eliminada') } catch (e: any) { toastError(getErrorMessage(e)) } }}>Eliminar</button>
                            </td>
                        </tr>
                    ))}
                    {!loading && view.length === 0 && (<tr><td className="py-3 px-3 text-gray-500" colSpan={6}>Sin registros</td></tr>)}
                </tbody>
            </table>
            <Pagination page={page} setPage={setPage} totalPages={totalPages} />
        </div>
    )
}
