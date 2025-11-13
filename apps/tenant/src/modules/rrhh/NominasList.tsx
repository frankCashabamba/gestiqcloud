import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listNominas, removeNomina, type Nomina } from './services/nomina'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'

export default function NominasList() {
    const [items, setItems] = useState<Nomina[]>([])
    const [loading, setLoading] = useState(false)
    const [errMsg, setErrMsg] = useState<string | null>(null)
    const nav = useNavigate()
    const { success, error: toastError } = useToast()
    const [q, setQ] = useState('')

    useEffect(() => {
        (async () => {
            try {
                setLoading(true)
                setItems(await listNominas())
            } catch (e: any) {
                const m = getErrorMessage(e)
                setErrMsg(m)
                toastError(m)
            } finally {
                setLoading(false)
            }
        })()
    }, [])

    const [sortKey, setSortKey] = useState<'numero' | 'periodo_mes' | 'status'>('numero')
    const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
    const [per, setPer] = useState(10)
    const filtered = useMemo(() => items.filter(n =>
        (n.numero || '').toLowerCase().includes(q.toLowerCase()) ||
        (n.empleado_id || '').toString().toLowerCase().includes(q.toLowerCase())
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
            calculated: 'Calculada',
            approved: 'Aprobada',
            paid: 'Pagada',
            cancelled: 'Cancelada'
        }
        return map[s || 'draft'] || s
    }

    const formatCurrency = (val?: number) => val ? `€${val.toFixed(2)}` : '-'

    return (
        <div className="p-4">
            <div className="flex justify-between items-center mb-3">
                <h2 className="font-semibold text-lg">Nóminas</h2>
                <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={() => nav('nuevo')}>Nueva</button>
            </div>
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar número o empleado..." className="mb-3 w-full px-3 py-2 border rounded text-sm" />
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
                        <th>Empleado</th>
                        <th><button className="underline" onClick={() => { setSortKey('periodo_mes'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>Periodo {sortKey === 'periodo_mes' ? (sortDir === 'asc' ? '▲' : '▼') : ''}</button></th>
                        <th>Líquido Total</th>
                        <th><button className="underline" onClick={() => { setSortKey('status'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>Estado {sortKey === 'status' ? (sortDir === 'asc' ? '▲' : '▼') : ''}</button></th>
                        <th>Acciones</th>
                    </tr>
                </thead>
                <tbody>
                    {view.map((n) => (
                        <tr key={n.id} className="border-b">
                            <td>{n.numero || '-'}</td>
                            <td>{n.empleado_id}</td>
                            <td>{n.periodo_mes}/{n.periodo_ano}</td>
                            <td>{formatCurrency(n.liquido_total)}</td>
                            <td>{statusLabel(n.status)}</td>
                            <td>
                                <Link to={`${n.id}/editar`} className="text-blue-600 hover:underline mr-3">Editar</Link>
                                <button className="text-red-700" onClick={async () => {
                                    if (!confirm('¿Eliminar nómina?')) return
                                    try {
                                        await removeNomina(n.id)
                                        setItems((p) => p.filter(x => x.id !== n.id))
                                        success('Nómina eliminada')
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
