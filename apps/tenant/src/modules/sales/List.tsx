import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { listVentas, removeVenta, type Venta } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import StatusBadge from './components/StatusBadge'
import { PAGINATION_DEFAULTS } from '../../constants/defaults'
import { getCompanySettings, formatCurrency, type CompanySettings } from '../../services/companySettings'
import { usePermission } from '../../hooks/usePermission'
import ProtectedButton from '../../components/ProtectedButton'

export default function VentasList() {
    const { t } = useTranslation()
    const can = usePermission()
    const [items, setItems] = useState<Venta[]>([])
    const [loading, setLoading] = useState(false)
    const [errMsg, setErrMsg] = useState<string | null>(null)
    const [companySettings, setCompanySettings] = useState<CompanySettings | null>(null)
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

    useEffect(() => {
        ;(async () => {
            try {
                setCompanySettings(await getCompanySettings())
            } catch {
                setCompanySettings(null)
            }
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
            if (sortKey === 'total') return ((Number(av) || 0) - (Number(bv) || 0)) * dir
            return (av < bv ? -1 : av > bv ? 1 : 0) * dir
        })
    }, [filtered, sortKey, sortDir])

    const { page, setPage, totalPages, view, setPerPage } = usePagination(sorted, per)
    useEffect(() => setPerPage(per), [per, setPerPage])

    function exportCSV(rows: Venta[]) {
        const header = ['id', 'numero', 'fecha', 'cliente', 'total', 'estado']
        const body = rows.map(r => [
            r.id,
            r.numero ?? '',
            r.fecha,
            r.cliente_nombre ?? '',
            Number(r.total ?? 0),
            r.estado ?? '',
        ])
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
                <h2 className="font-semibold text-lg">{t('sales.title')}</h2>
                <div className="flex gap-2">
                    {can('sales:read') && (
                        <ProtectedButton
                            permission="sales:read"
                            variant="secondary"
                            onClick={() => exportCSV(view)}
                        >
                            {t('sales.exportCsv')}
                        </ProtectedButton>
                    )}
                    {can('sales:create') && (
                        <ProtectedButton
                            permission="sales:create"
                            variant="primary"
                            onClick={() => nav('new')}
                        >
                            {t('common.new')}
                        </ProtectedButton>
                    )}
                </div>
            </div>
            <div className="mb-3 flex flex-wrap items-end gap-3">
                <div>
                    <label className="text-sm mr-2 block">{t('common.status')}</label>
                    <select value={estado} onChange={(e) => setEstado(e.target.value)} className="border px-2 py-1 rounded text-sm">
                        <option value="">{t('common.all')}</option>
                        <option value="borrador">{t('sales.draft')}</option>
                        <option value="emitida">{t('sales.issued')}</option>
                        <option value="anulada">{t('sales.voided')}</option>
                    </select>
                </div>
                <div>
                    <label className="text-sm mr-2 block">{t('common.from')}</label>
                    <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className="border px-2 py-1 rounded text-sm" />
                </div>
                <div>
                    <label className="text-sm mr-2 block">{t('common.to')}</label>
                    <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className="border px-2 py-1 rounded text-sm" />
                </div>
                <div>
                    <label className="text-sm mr-2 block">{t('common.search')}</label>
                    <input placeholder={t('sales.searchPlaceholder')} value={q} onChange={(e) => setQ(e.target.value)} className="border px-2 py-1 rounded text-sm" style={{ minWidth: 200 }} />
                </div>
            </div>
            {loading && <div className="text-sm text-gray-500">{t('common.loading')}</div>}
            {errMsg && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{errMsg}</div>}
            <div className="flex items-center gap-3 mb-2 text-sm">
                <label>{t('common.perPage')}</label>
                <select value={per} onChange={(e) => setPer(Number(e.target.value))} className="border px-2 py-1 rounded">
                    <option value={10}>10</option>
                    <option value={25}>25</option>
                    <option value={50}>50</option>
                </select>
            </div>
            <table className="min-w-full text-sm">
                <thead>
                    <tr className="text-left border-b">
                        <th className="py-2"><button className="underline" onClick={() => { setSortKey('numero'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>{t('sales.saleNumber')} {sortKey === 'numero' ? (sortDir === 'asc' ? '↑' : '↓') : ''}</button></th>
                        <th className="py-2">{t('sales.customer')}</th>
                        <th className="py-2"><button className="underline" onClick={() => { setSortKey('fecha'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>{t('common.date')} {sortKey === 'fecha' ? (sortDir === 'asc' ? '↑' : '↓') : ''}</button></th>
                        <th className="py-2"><button className="underline" onClick={() => { setSortKey('total'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>{t('common.total')} {sortKey === 'total' ? (sortDir === 'asc' ? '↑' : '↓') : ''}</button></th>
                        <th className="py-2"><button className="underline" onClick={() => { setSortKey('estado'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>{t('common.status')} {sortKey === 'estado' ? (sortDir === 'asc' ? '↑' : '↓') : ''}</button></th>
                        <th className="py-2">{t('common.actions')}</th>
                    </tr>
                </thead>
                <tbody>
                    {view.map((v) => (
                        <tr key={v.id} className="border-b hover:bg-gray-50">
                            <td className="py-2">{v.numero || '-'}</td>
                            <td className="py-2">{v.cliente_nombre || '-'}</td>
                            <td className="py-2">{v.fecha}</td>
                            <td className="py-2 font-semibold">
                                {v.total !== null && v.total !== undefined && Number.isFinite(Number(v.total))
                                    ? formatCurrency(Number(v.total), companySettings || undefined)
                                    : '-'}
                            </td>
                            <td className="py-2"><StatusBadge estado={v.estado} /></td>
                            <td className="py-2">
                                {can('sales:read') && (
                                    <Link to={`${v.id}`} className="text-blue-600 hover:underline mr-3">
                                        {t('common.view')}
                                    </Link>
                                )}
                                {can('sales:update') && (
                                    <Link to={`${v.id}/editar`} className="text-blue-600 hover:underline mr-3">
                                        {t('common.edit')}
                                    </Link>
                                )}
                                {v.estado === 'borrador' && can('sales:update') && (
                                    <button
                                        className="text-green-700 hover:underline mr-3"
                                        onClick={() => nav(`${v.id}/facturar`)}
                                    >
                                        {t('sales.invoice')}
                                    </button>
                                )}
                                {can('sales:delete') && (
                                    <ProtectedButton
                                        permission="sales:delete"
                                        variant="ghost"
                                        onClick={async () => {
                                            if (!confirm(t('sales.deleteConfirm'))) return
                                            try {
                                                await removeVenta(v.id)
                                                setItems((p) => p.filter(x => x.id !== v.id))
                                                success(t('sales.deleted'))
                                            } catch (e: any) {
                                                toastError(getErrorMessage(e))
                                            }
                                        }}
                                    >
                                        {t('common.delete')}
                                    </ProtectedButton>
                                )}
                            </td>
                        </tr>
                    ))}
                    {!loading && view.length === 0 && (<tr><td className="py-3 px-3 text-gray-500" colSpan={6}>{t('common.noRecords')}</td></tr>)}
                </tbody>
            </table>
            <Pagination page={page} setPage={setPage} totalPages={totalPages} />
        </div>
    )
}
