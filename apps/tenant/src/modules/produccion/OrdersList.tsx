import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listProductionOrders, removeProductionOrder, type ProductionOrder } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'

export default function OrdersList() {
    const [items, setItems] = useState<ProductionOrder[]>([])
    const [loading, setLoading] = useState(false)
    const [errMsg, setErrMsg] = useState<string | null>(null)
    const nav = useNavigate()
    const { success, error: toastError } = useToast()
    const [q, setQ] = useState('')

    useEffect(() => {
        (async () => {
            try {
                setLoading(true)
                setItems(await listProductionOrders())
            } catch (e: any) {
                const m = getErrorMessage(e)
                setErrMsg(m)
                toastError(m)
            } finally {
                setLoading(false)
            }
        })()
    }, [])

    const [sortKey, setSortKey] = useState<'numero' | 'status' | 'scheduled_date'>('numero')
    const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
    const [per, setPer] = useState(10)
    const filtered = useMemo(() => items.filter(o =>
        (o.numero || '').toLowerCase().includes(q.toLowerCase()) ||
        (o.batch_number || '').toLowerCase().includes(q.toLowerCase()) ||
        (o.notes || '').toLowerCase().includes(q.toLowerCase())
    ), [items, q])
    const sorted = useMemo(() => {
        const dir = sortDir === 'asc' ? 1 : -1
        return [...filtered].sort((a, b) => {
            const av = ((a as any)[sortKey] || '').toString().toLowerCase()
            const bv = ((b as any)[sortKey] || '').toString().toLowerCase()
            return av < bv ? -1 * dir : av > bv ? 1 * dir : 0
        })
    }, [filtered, sortKey, sortDir])
    const { page, setPage, totalPages, view, perPage, setPerPage } = usePagination(sorted, per)
    useEffect(() => setPerPage(per), [per, setPerPage])

    const statusLabel = (s?: string) => {
        const map: Record<string, string> = {
            draft: 'Borrador',
            scheduled: 'Programada',
            in_progress: 'En Proceso',
            completed: 'Completada',
            cancelled: 'Cancelada'
        }
        return map[s || 'draft'] || s
    }

    return (
        <div className="p-4">
            <div className="flex justify-between items-center mb-3">
                <h2 className="font-semibold text-lg">Órdenes de Producción</h2>
                <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={() => nav('nuevo')}>Nueva</button>
            </div>
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar número, lote o notas..." className="mb-3 w-full px-3 py-2 border rounded text-sm" />
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
                        <th><button className="underline" onClick={() => { setSortKey('numero'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>Número {sortKey === 'numero' ? (sortDir === 'asc' ? '▲' : '▼') : ''}</button></th>
                        <th><button className="underline" onClick={() => { setSortKey('status'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>Estado {sortKey === 'status' ? (sortDir === 'asc' ? '▲' : '▼') : ''}</button></th>
                        <th><button className="underline" onClick={() => { setSortKey('scheduled_date'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>Fecha {sortKey === 'scheduled_date' ? (sortDir === 'asc' ? '▲' : '▼') : ''}</button></th>
                        <th>Cant. Planificada</th>
                        <th>Cant. Producida</th>
                        <th>Acciones</th>
                    </tr>
                </thead>
                <tbody>
                    {view.map((o) => (
                        <tr key={o.id} className="border-b">
                            <td>{o.numero || '-'}</td>
                            <td>{statusLabel(o.status)}</td>
                            <td>{o.scheduled_date || '-'}</td>
                            <td>{o.qty_planned}</td>
                            <td>{o.qty_produced || 0}</td>
                            <td>
                                <Link to={`${o.id}/editar`} className="text-blue-600 hover:underline mr-3">Editar</Link>
                                <button className="text-red-700" onClick={async () => {
                                    if (!confirm('¿Eliminar orden de producción?')) return
                                    try {
                                        await removeProductionOrder(o.id)
                                        setItems((p) => p.filter(x => x.id !== o.id))
                                        success('Orden eliminada')
                                    } catch (e: any) {
                                        toastError(getErrorMessage(e))
                                    }
                                }}>Eliminar</button>
                            </td>
                        </tr>
                    ))}
                    {!loading && items.length === 0 && (<tr><td className="py-3 px-3" colSpan={6}>Sin registros</td></tr>)}
                </tbody>
            </table>
            <Pagination page={page} setPage={setPage} totalPages={totalPages} />
        </div>
    )
}
