import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
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
    if (estado === 'entregado') {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-800">
                ✓ Entregado
            </span>
        )
    }
    if (estado === 'facturada' || estado === 'invoiced') {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
                ✓ Facturado
            </span>
        )
    }
    if (estado === 'confirmed' || estado === 'emitida') {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-cyan-100 text-cyan-800">
                ✓ Confirmado
            </span>
        )
    }
    return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
            ⏳ PDT confirmar
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
    async function handleCobrar(v: Venta) {
        if (!confirm(`¿Cobrar y facturar "${v.numero || v.id}" por ${formatCurrency(Number(v.total ?? 0), companySettings || undefined)}?`)) return
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
            success('Pedido confirmado')
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
            success('Pedido marcado como entregado ✓')
        } catch (e: any) {
            toastError(getErrorMessage(e))
        } finally {
            setEntregandoId(null)
        }
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

    const deliveryLabel = isTaller ? 'Entrega estimada' : 'Fecha evento'

    return (
        <div className="p-4">
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
                    Todas las ventas
                </button>
                {isSpecial && (
                    <button
                        className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === 'pedidos' ? 'border-amber-500 text-amber-700' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                        onClick={() => { setTab('pedidos'); setEstado('') }}
                    >
                        {isTaller ? '🔧 Trabajos' : '🎂 Pedidos'}
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
                            {s === '' ? 'Todos' : s === 'borrador' ? 'Borrador' : s === 'emitida' ? 'Emitida' : 'Anulada'}
                        </button>
                    ))}
                </div>
            )}

            {/* Barra de búsqueda */}
            <div className="flex flex-wrap gap-3 mb-3 items-end">
                <input
                    placeholder={tab === 'pedidos' ? 'Buscar cliente, número, notas...' : t('sales.searchPlaceholder')}
                    value={q}
                    onChange={e => setQ(e.target.value)}
                    className="border px-3 py-1.5 rounded text-sm flex-1 min-w-48"
                />
                {tab === 'todas' && (
                    <>
                        <div className="flex items-center gap-1">
                            <label className="text-xs text-slate-500">Desde</label>
                            <input type="date" value={desde} onChange={e => setDesde(e.target.value)} className="border px-2 py-1 rounded text-sm" />
                        </div>
                        <div className="flex items-center gap-1">
                            <label className="text-xs text-slate-500">Hasta</label>
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
                        Solo PDT confirmar
                    </label>
                )}
            </div>

            {loading && <div className="text-sm text-gray-500">{t('common.loading')}</div>}

            {/* Leyenda de colores (solo tab pedidos) */}
            {tab === 'pedidos' && (
                <div className="flex flex-wrap gap-3 mb-3 text-xs text-slate-600">
                    <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-orange-500 inline-block"/>Entrega hoy</span>
                    <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-yellow-400 inline-block"/>Entrega mañana</span>
                    <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-blue-400 inline-block"/>Próxima entrega</span>
                    <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-gray-300 inline-block"/>Entrega pasada</span>
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
                                <td className="py-2 px-2">{v.cliente_nombre || <span className="text-gray-400">Sin cliente</span>}</td>
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
                                                {cobrandoId === v.id ? '...' : '💵 Cobrar'}
                                            </button>
                                        )}
                                        {can('sales:delete') && !isPosReadOnly(v) && !['facturada', 'invoiced'].includes((v.estado || '').toLowerCase()) && (
                                            <ProtectedButton
                                                permission="sales:delete"
                                                variant="ghost"
                                                onClick={async () => {
                                                    if (!confirm(t('sales.deleteConfirm'))) return
                                                    try {
                                                        const { removeVenta } = await import('./services')
                                                        await removeVenta(v.id)
                                                        setItems(p => p.filter(x => x.id !== v.id))
                                                        success(t('sales.deleted'))
                                                    } catch (e: any) { toastError(getErrorMessage(e)) }
                                                }}
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
                            <th className="py-2 px-2">Cliente / Notas</th>
                            <th className="py-2 px-2">{deliveryLabel}</th>
                            <th className="py-2 px-2">Total</th>
                            <th className="py-2 px-2">Anticipo</th>
                            <th className="py-2 px-2">Estado</th>
                            <th className="py-2 px-2">Acciones</th>
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
                                        <div className="font-medium">{v.cliente_nombre || <span className="text-gray-400">Sin cliente</span>}</div>
                                        {v.notas && <div className="text-xs text-gray-500 truncate max-w-40">{v.notas}</div>}
                                    </td>
                                    <td className="py-2 px-2">
                                        {dd ? (
                                            <span className={`font-medium ${isDueToday ? 'text-orange-700 font-bold' : isDueTomorrow ? 'text-yellow-700' : isPastDelivery ? 'text-gray-400' : 'text-blue-700'}`}>
                                                {dd}
                                                {isDueToday && <span className="ml-1 text-xs bg-orange-500 text-white px-1.5 py-0.5 rounded-full">HOY</span>}
                                                {isDueTomorrow && <span className="ml-1 text-xs bg-yellow-500 text-white px-1.5 py-0.5 rounded-full">Mañana</span>}
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
                                                <Link to={`${v.id}/edit`} className="text-blue-600 hover:underline text-xs">Editar</Link>
                                            )}
                                            {isPending && can('sales:update') && (
                                                <>
                                                    <button
                                                        onClick={() => handleConfirmar(v)}
                                                        className="text-xs text-green-700 hover:underline font-medium"
                                                    >
                                                        Confirmar
                                                    </button>
                                                    <button
                                                        disabled={cobrandoId === v.id}
                                                        onClick={() => handleCobrar(v)}
                                                        className="px-2 py-0.5 text-xs rounded font-semibold bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
                                                    >
                                                        {cobrandoId === v.id ? '...' : '💵 Cobrar'}
                                                    </button>
                                                </>
                                            )}
                                            {isInvoiced && !isEntregado && can('sales:update') && (
                                                <button
                                                    disabled={entregandoId === v.id}
                                                    onClick={() => handleMarcarEntregado(v)}
                                                    className="px-2 py-0.5 text-xs rounded font-semibold bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
                                                >
                                                    {entregandoId === v.id ? '...' : '🚚 PDT Entregar'}
                                                </button>
                                            )}
                                            {isEntregado && (
                                                <span className="text-xs text-green-700 font-semibold">✓ Entregado</span>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            )
                        })}
                        {!loading && view.length === 0 && (
                            <tr>
                                <td colSpan={7} className="py-6 text-center text-gray-500">
                                    No hay {isTaller ? 'trabajos' : 'pedidos'} con fecha de entrega registrada
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            )}

            <Pagination page={page} setPage={setPage} totalPages={totalPages} />
        </div>
    )
}
