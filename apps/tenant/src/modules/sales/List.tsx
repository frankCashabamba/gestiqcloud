import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { BackButton } from '@ui'
import { useTranslation } from 'react-i18next'
import { useCompanyConfig } from '../../contexts/CompanyConfigContext'
import { listVentas, updateVenta, checkoutOrder, isPosReadOnly, type Venta } from './services'
import { clearInvoicesCache } from '../billing/services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import StatusBadge from './components/StatusBadge'
import { getCompanySettings, formatCurrency, type CompanySettings } from '../../services/companySettings'
import { usePermission } from '../../hooks/usePermission'
import ProtectedButton from '../../components/ProtectedButton'
import SalesDailyChart from './SalesDailyChart'

const BAKERY_SECTORS = new Set(['panaderia', 'panaderia_pro'])
const WORKSHOP_SECTORS = new Set(['taller', 'taller_pro'])
const SPECIAL_SECTORS = new Set(['panaderia', 'panaderia_pro', 'taller', 'taller_pro'])

type Tab = 'todas' | 'pedidos'

function ConfirmBadge({ estado }: { estado?: string }) {
    const { t } = useTranslation()
    if (estado === 'entregado') {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-800">
                ✓ {t('sales.statusDelivered')}
            </span>
        )
    }
    if (estado === 'facturada' || estado === 'invoiced') {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
                ✓ {t('sales.statusInvoiced')}
            </span>
        )
    }
    if (estado === 'confirmed' || estado === 'emitida') {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-cyan-100 text-cyan-800">
                ✓ {t('sales.statusConfirmed')}
            </span>
        )
    }
    return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
            ⏳ {t('sales.statusPendingConfirm')}
        </span>
    )
}

function DepositBadge({ amount, paid }: { amount?: number; paid?: boolean }) {
    if (!amount || amount <= 0) return <span className="text-gray-400 text-xs">—</span>
    return (
        <span className={`text-xs font-medium ${paid ? 'text-green-700' : 'text-amber-700'}`}>
            {paid ? '✓' : '⏳'} ${Number(amount).toFixed(2)}
        </span>
    )
}

export default function VentasList() {
    const { t } = useTranslation()
    const can = usePermission()
    const { config } = useCompanyConfig()
    const sector = config?.sector?.plantilla || ''
    const isSpecial = SPECIAL_SECTORS.has(sector)
    const isTaller = WORKSHOP_SECTORS.has(sector)
    const nav = useNavigate()
    const { success, error: toastError } = useToast()

    const [items, setItems] = useState<Venta[]>([])
    const [loading, setLoading] = useState(false)
    const [companySettings, setCompanySettings] = useState<CompanySettings | null>(null)
    const [tab, setTab] = useState<Tab>('todas')
    const [q, setQ] = useState('')
    const [estado, setEstado] = useState('')
    const [desde, setDesde] = useState('')
    const [hasta, setHasta] = useState('')
    const [cobrandoId, setCobrandoId] = useState<string | number | null>(null)
    const [cobrarTarget, setCobrarTarget] = useState<Venta | null>(null)
    const [deleteTarget, setDeleteTarget] = useState<string | number | null>(null)

    useEffect(() => {
        setLoading(true)
        Promise.all([listVentas(), getCompanySettings().catch(() => null)])
            .then(([ventas, settings]) => {
                setItems(ventas)
                setCompanySettings(settings)
            })
            .catch(e => toastError(getErrorMessage(e)))
            .finally(() => setLoading(false))
    }, [])

    // --- Cobrar: genera factura + gasto de receta en una sola operación ---
    function handleCobrar(v: Venta) {
        setCobrarTarget(v)
    }

    async function doCobrar() {
        if (!cobrarTarget) return
        const v = cobrarTarget
        setCobrarTarget(null)
        setCobrandoId(v.id)
        try {
            const result = await checkoutOrder(String(v.id))
            clearInvoicesCache()
            setItems(prev => prev.map(x => x.id === v.id ? { ...x, estado: 'facturada' } : x))
            success(result.message)
        } catch (e: any) {
            toastError(getErrorMessage(e))
        } finally {
            setCobrandoId(null)
        }
    }

    async function handleConfirmar(v: Venta) {
        try {
            await updateVenta(v.id, { ...v, lineas: v.lineas, estado: 'emitida' } as any)
            setItems(prev => prev.map(x => x.id === v.id ? { ...x, estado: 'emitida' } : x))
            success(t('sales.orderConfirmed'))
        } catch (e: any) {
            toastError(getErrorMessage(e))
        }
    }

    const [entregandoId, setEntregandoId] = useState<string | number | null>(null)

    async function handleMarcarEntregado(v: Venta) {
        setEntregandoId(v.id)
        try {
            await updateVenta(v.id, { ...v, lineas: v.lineas, estado: 'entregado' } as any)
            setItems(prev => prev.map(x => x.id === v.id ? { ...x, estado: 'entregado' } : x))
            success(t('sales.orderDelivered'))
        } catch (e: any) {
            toastError(getErrorMessage(e))
        } finally {
            setEntregandoId(null)
        }
    }

    async function doDelete() {
        if (!deleteTarget) return
        const id = deleteTarget
        setDeleteTarget(null)
        try {
            const { removeVenta } = await import('./services')
            await removeVenta(id)
            setItems(p => p.filter(x => x.id !== id))
            success(t('sales.deleted'))
        } catch (e: any) { toastError(getErrorMessage(e)) }
    }

    // --- Filtrado por tab ---
    const tabItems = useMemo(() => {
        if (tab === 'pedidos') return items.filter(v => !!v.delivery_date)
        return items
    }, [items, tab])

    // --- Filtros adicionales ---
    const filtered = useMemo(() => tabItems.filter(v => {
        if (estado && (v.estado || '') !== estado) return false
        if (desde && v.fecha < desde) return false
        if (hasta && v.fecha > hasta) return false
        if (q && !(
            `${v.id}`.includes(q) ||
            (v.numero || '').toLowerCase().includes(q.toLowerCase()) ||
            (v.cliente_nombre || '').toLowerCase().includes(q.toLowerCase()) ||
            (v.notas || '').toLowerCase().includes(q.toLowerCase())
        )) return false
        return true
    }), [tabItems, estado, desde, hasta, q])

    const sorted = useMemo(() => {
        if (tab === 'pedidos') {
            return [...filtered].sort((a, b) => {
                const da = a.delivery_date || ''
                const db_ = b.delivery_date || ''
                return da < db_ ? -1 : da > db_ ? 1 : 0
            })
        }
        return [...filtered].sort((a, b) => (a.fecha < b.fecha ? 1 : -1))
    }, [filtered, tab])

    const { page, setPage, totalPages, view } = usePagination(sorted, 25)

    function exportCSV() {
        const header = ['id', 'numero', 'fecha', 'cliente', 'total', 'estado']
        const body = view.map(r => [r.id, r.numero ?? '', r.fecha, r.cliente_nombre ?? '', Number(r.total ?? 0), r.estado ?? ''])
        const csv = [header, ...body].map(line => line.join(',')).join('\n')
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url; a.download = `ventas-${new Date().toISOString().slice(0, 10)}.csv`; a.click()
        URL.revokeObjectURL(url)
    }

    const deliveryLabel = isTaller ? t('sales.deliveryLabelTaller') : t('sales.deliveryLabelPanaderia')

    return (
        <div className="p-4">
            <div style={{ marginBottom: '0.75rem' }}><BackButton onClick={() => nav(-1)} /></div>
            <SalesDailyChart items={items} companySettings={companySettings} />

            {/* Header */}
            <div className="flex justify-between items-center mb-3">
                <h2 className="font-semibold text-lg">{t('sales.title')}</h2>
                <div className="flex gap-2">
                    {can('sales:read') && (
                        <ProtectedButton permission="sales:read" variant="secondary" onClick={exportCSV}>
                            {t('sales.exportCsv')}
                        </ProtectedButton>
                    )}
                    {can('sales:create') && (
                        <ProtectedButton permission="sales:create" variant="primary" onClick={() => nav('new')}>
                            {t('common.new')}
                        </ProtectedButton>
                    )}
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 mb-4 border-b">
                <button
                    className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === 'todas' ? 'border-blue-600 text-blue-700' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                    onClick={() => { setTab('todas'); setEstado('') }}
                >
                    {t('sales.allSales')}
                </button>
                {isSpecial && (
                    <button
                        className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === 'pedidos' ? 'border-amber-500 text-amber-700' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                        onClick={() => { setTab('pedidos'); setEstado('') }}
                    >
                        {isTaller ? t('sales.tabWorks') : t('sales.tabOrders')}
                        {items.filter(v => v.delivery_date && !['emitida', 'confirmed', 'facturada', 'invoiced', 'anulada', 'cancelled'].includes(v.estado ?? '')).length > 0 && (
                            <span className="ml-1.5 bg-amber-500 text-white text-xs rounded-full px-1.5 py-0.5">
                                {items.filter(v => v.delivery_date && !['emitida', 'confirmed', 'facturada', 'invoiced', 'anulada', 'cancelled'].includes(v.estado ?? '')).length}
                            </span>
                        )}
                    </button>
                )}
            </div>

            {/* Filtros rápidos de estado (solo en tab "todas") */}
            {tab === 'todas' && (
                <div className="flex flex-wrap gap-2 mb-3">
                    {['', 'borrador', 'emitida', 'anulada'].map(s => (
                        <button
                            key={s}
                            onClick={() => setEstado(s)}
                            className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                                estado === s
                                    ? 'bg-blue-600 text-white border-blue-600'
                                    : 'bg-white text-slate-600 border-slate-300 hover:border-blue-400'
                            }`}
                        >
                            {s === '' ? t('sales.allStatuses') : s === 'borrador' ? t('sales.draft') : s === 'emitida' ? t('sales.issued') : t('sales.voided')}
                        </button>
                    ))}
                </div>
            )}

            {/* Barra de búsqueda */}
            <div className="flex flex-wrap gap-3 mb-3 items-end">
                <input
                    placeholder={tab === 'pedidos' ? t('sales.ordersSearchPlaceholder') : t('sales.searchPlaceholder')}
                    value={q}
                    onChange={e => setQ(e.target.value)}
                    className="border px-3 py-1.5 rounded text-sm flex-1 min-w-48"
                />
                {tab === 'todas' && (
                    <>
                        <div className="flex items-center gap-1">
                            <label className="text-xs text-slate-500">{t('common.from')}</label>
                            <input type="date" value={desde} onChange={e => setDesde(e.target.value)} className="border px-2 py-1 rounded text-sm" />
                        </div>
                        <div className="flex items-center gap-1">
                            <label className="text-xs text-slate-500">{t('common.to')}</label>
                            <input type="date" value={hasta} onChange={e => setHasta(e.target.value)} className="border px-2 py-1 rounded text-sm" />
                        </div>
                    </>
                )}
                {tab === 'pedidos' && (
                    <label className="flex items-center gap-2 text-sm cursor-pointer">
                        <input
                            type="checkbox"
                            checked={estado === 'borrador'}
                            onChange={e => setEstado(e.target.checked ? 'borrador' : '')}
                        />
                        {t('sales.pendingConfirmFilter')}
                    </label>
                )}
            </div>

            {loading && <div className="text-sm text-gray-500">{t('common.loading')}</div>}

            {/* Leyenda de colores (solo tab pedidos) */}
            {tab === 'pedidos' && (
                <div className="flex flex-wrap gap-3 mb-3 text-xs text-slate-600">
                    <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-orange-500 inline-block"/>{t('sales.deliveryToday')}</span>
                    <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-yellow-400 inline-block"/>{t('sales.deliveryTomorrow')}</span>
                    <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-blue-400 inline-block"/>{t('sales.deliveryUpcoming')}</span>
                    <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-gray-300 inline-block"/>{t('sales.deliveryPast')}</span>
                </div>
            )}

            {/* Tabla "Todas" */}
            {tab === 'todas' && (
                <table className="min-w-full text-sm">
                    <thead>
                        <tr className="text-left border-b bg-gray-50">
                            <th className="py-2 px-2">{t('sales.saleNumber')}</th>
                            <th className="py-2 px-2">{t('sales.customer')}</th>
                            <th className="py-2 px-2">{t('common.date')}</th>
                            <th className="py-2 px-2">{t('common.total')}</th>
                            <th className="py-2 px-2">{t('common.status')}</th>
                            <th className="py-2 px-2">{t('common.actions')}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {view.map(v => (
                            <tr key={v.id} className="border-b hover:bg-gray-50">
                                <td className="py-2 px-2 font-mono text-xs">{v.numero || '—'}</td>
                                <td className="py-2 px-2">{v.cliente_nombre || <span className="text-gray-400">{t('sales.noCustomer')}</span>}</td>
                                <td className="py-2 px-2">{v.fecha}</td>
                                <td className="py-2 px-2 font-semibold">
                                    {v.total !== null && v.total !== undefined && Number.isFinite(Number(v.total))
                                        ? formatCurrency(Number(v.total), companySettings || undefined)
                                        : '—'}
                                </td>
                                <td className="py-2 px-2"><StatusBadge estado={v.estado} /></td>
                                <td className="py-2 px-2">
                                    <div className="flex gap-2 flex-wrap items-center">
                                        {can('sales:read') && (
                                            <Link to={`${v.id}`} className="text-blue-600 hover:underline text-xs">{t('common.view')}</Link>
                                        )}
                                        {can('sales:update') && !isPosReadOnly(v) && !['facturada', 'invoiced'].includes((v.estado || '').toLowerCase()) && (
                                            <Link to={`${v.id}/edit`} className="text-blue-600 hover:underline text-xs">{t('common.edit')}</Link>
                                        )}
                                        {v.pos_receipt_id && isPosReadOnly(v) && (
                                            <span className="text-xs text-slate-400 italic">POS</span>
                                        )}
                                        {v.estado === 'borrador' && can('sales:update') && (
                                            <button
                                                disabled={cobrandoId === v.id}
                                                onClick={() => handleCobrar(v)}
                                                className="px-2 py-0.5 text-xs rounded font-semibold bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
                                            >
                                                {cobrandoId === v.id ? '...' : t('sales.chargeOrder')}
                                            </button>
                                        )}
                                        {can('sales:delete') && !isPosReadOnly(v) && !['facturada', 'invoiced'].includes((v.estado || '').toLowerCase()) && (
                                            <ProtectedButton
                                                permission="sales:delete"
                                                variant="ghost"
                                                onClick={() => setDeleteTarget(v.id)}
                                            >
                                                {t('common.delete')}
                                            </ProtectedButton>
                                        )}
                                    </div>
                                </td>
                            </tr>
                        ))}
                        {!loading && view.length === 0 && (
                            <tr><td colSpan={6} className="py-6 text-center text-gray-500">{t('common.noRecords')}</td></tr>
                        )}
                    </tbody>
                </table>
            )}

            {/* Tabla "Pedidos" */}
            {tab === 'pedidos' && (
                <table className="min-w-full text-sm">
                    <thead>
                        <tr className="text-left border-b bg-amber-50">
                            <th className="py-2 px-2">#</th>
                            <th className="py-2 px-2">{t('sales.colCustomerNotes')}</th>
                            <th className="py-2 px-2">{deliveryLabel}</th>
                            <th className="py-2 px-2">{t('common.total')}</th>
                            <th className="py-2 px-2">{t('sales.colDeposit')}</th>
                            <th className="py-2 px-2">{t('common.status')}</th>
                            <th className="py-2 px-2">{t('common.actions')}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {view.map(v => {
                            const isPending = !['confirmed', 'emitida', 'facturada', 'invoiced', 'entregado', 'anulada', 'cancelled'].includes(v.estado ?? '')
                            const isInvoiced = ['facturada', 'invoiced'].includes(v.estado ?? '')
                            const isEntregado = v.estado === 'entregado'
                            const today = new Date().toISOString().slice(0, 10)
                            const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10)
                            const dd = v.delivery_date || ''
                            const isPastDelivery = dd && dd < today
                            const isDueToday = dd === today
                            const isDueTomorrow = dd === tomorrow
                            const rowClass = isEntregado || !dd || isPastDelivery
                                ? 'border-b hover:bg-gray-50 opacity-60'
                                : isDueToday
                                    ? 'border-b bg-orange-50 border-l-4 border-l-orange-500 hover:bg-orange-100'
                                    : isDueTomorrow
                                        ? 'border-b bg-yellow-50 border-l-4 border-l-yellow-400 hover:bg-yellow-100'
                                        : 'border-b bg-blue-50 border-l-4 border-l-blue-400 hover:bg-blue-100'
                            return (
                                <tr key={v.id} className={rowClass}>
                                    <td className="py-2 px-2 font-mono text-xs">{v.numero || '—'}</td>
                                    <td className="py-2 px-2">
                                        <div className="font-medium">{v.cliente_nombre || <span className="text-gray-400">{t('sales.noCustomer')}</span>}</div>
                                        {v.notas && <div className="text-xs text-gray-500 truncate max-w-40">{v.notas}</div>}
                                    </td>
                                    <td className="py-2 px-2">
                                        {dd ? (
                                            <span className={`font-medium ${isDueToday ? 'text-orange-700 font-bold' : isDueTomorrow ? 'text-yellow-700' : isPastDelivery ? 'text-gray-400' : 'text-blue-700'}`}>
                                                {dd}
                                                {isDueToday && <span className="ml-1 text-xs bg-orange-500 text-white px-1.5 py-0.5 rounded-full">{t('sales.badgeToday')}</span>}
                                                {isDueTomorrow && <span className="ml-1 text-xs bg-yellow-500 text-white px-1.5 py-0.5 rounded-full">{t('sales.badgeTomorrow')}</span>}
                                            </span>
                                        ) : <span className="text-gray-400">—</span>}
                                    </td>
                                    <td className="py-2 px-2 font-semibold">
                                        {v.total !== null && v.total !== undefined
                                            ? formatCurrency(Number(v.total), companySettings || undefined)
                                            : '—'}
                                    </td>
                                    <td className="py-2 px-2">
                                        <DepositBadge amount={v.deposit_amount} paid={v.deposit_paid} />
                                    </td>
                                    <td className="py-2 px-2">
                                        <ConfirmBadge estado={v.estado} />
                                    </td>
                                    <td className="py-2 px-2">
                                        <div className="flex gap-2 flex-wrap items-center">
                                            {can('sales:update') && (
                                                <Link to={`${v.id}/edit`} className="text-blue-600 hover:underline text-xs">{t('common.edit')}</Link>
                                            )}
                                            {isPending && can('sales:update') && (
                                                <>
                                                    <button
                                                        onClick={() => handleConfirmar(v)}
                                                        className="text-xs text-green-700 hover:underline font-medium"
                                                    >
                                                        {t('sales.confirmOrder')}
                                                    </button>
                                                    <button
                                                        disabled={cobrandoId === v.id}
                                                        onClick={() => handleCobrar(v)}
                                                        className="px-2 py-0.5 text-xs rounded font-semibold bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
                                                    >
                                                        {cobrandoId === v.id ? '...' : t('sales.chargeOrder')}
                                                    </button>
                                                </>
                                            )}
                                            {isInvoiced && !isEntregado && can('sales:update') && (
                                                <button
                                                    disabled={entregandoId === v.id}
                                                    onClick={() => handleMarcarEntregado(v)}
                                                    className="px-2 py-0.5 text-xs rounded font-semibold bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
                                                >
                                                    {entregandoId === v.id ? '...' : t('sales.deliverOrder')}
                                                </button>
                                            )}
                                            {isEntregado && (
                                                <span className="text-xs text-green-700 font-semibold">✓ {t('sales.statusDelivered')}</span>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            )
                        })}
                        {!loading && view.length === 0 && (
                            <tr>
                                <td colSpan={7} className="py-6 text-center text-gray-500">
                                    {isTaller ? t('sales.worksEmpty') : t('sales.ordersEmpty')}
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            )}

            <Pagination page={page} setPage={setPage} totalPages={totalPages} />

            {cobrarTarget !== null && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setCobrarTarget(null)}>
                    <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-sm w-full mx-4" onClick={e => e.stopPropagation()}>
                        <div className="flex items-start gap-3 mb-5">
                            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                                <span className="text-lg">💵</span>
                            </div>
                            <div>
                                <h3 className="font-bold text-gray-900">{t('sales.chargeOrder')}</h3>
                                <p className="text-sm text-gray-500 mt-0.5">
                                    {t('sales.confirmCobrar', {
                                        number: cobrarTarget.numero || cobrarTarget.id,
                                        amount: formatCurrency(Number(cobrarTarget.total ?? 0), companySettings || undefined)
                                    })}
                                </p>
                            </div>
                        </div>
                        <div className="flex gap-2 justify-end">
                            <button
                                className="px-4 py-2 border border-gray-200 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
                                onClick={() => setCobrarTarget(null)}
                            >
                                {t('common.cancel')}
                            </button>
                            <button
                                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-xl text-sm font-semibold transition-colors"
                                onClick={() => void doCobrar()}
                            >
                                {t('sales.chargeOrder')}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {deleteTarget !== null && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setDeleteTarget(null)}>
                    <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-sm w-full mx-4" onClick={e => e.stopPropagation()}>
                        <div className="flex items-start gap-3 mb-5">
                            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                                <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                            </div>
                            <div>
                                <h3 className="font-bold text-gray-900">{t('sales.deleteConfirm')}</h3>
                            </div>
                        </div>
                        <div className="flex gap-2 justify-end">
                            <button
                                className="px-4 py-2 border border-gray-200 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
                                onClick={() => setDeleteTarget(null)}
                            >
                                {t('common.cancel')}
                            </button>
                            <button
                                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-sm font-semibold transition-colors"
                                onClick={() => void doDelete()}
                            >
                                {t('common.delete')}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
