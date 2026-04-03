import React, { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { BackButton } from '@ui'
import {
    cancelProductionOrder,
    completeProductionOrder,
    listProductionOrders,
    removeProductionOrder,
    startProductionOrder,
    type ProductionOrder,
} from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import ProductionAvailabilityGuard from './ProductionAvailabilityGuard'
import { useResolvedCompanyFeatures } from '../../contexts/CompanyConfigContext'
import { usePermission } from '../../hooks/usePermission'

type CompletionDraft = {
    qty_produced: string
    waste_qty: string
    waste_reason: string
    batch_number: string
    notes: string
}

const EMPTY_COMPLETION_DRAFT: CompletionDraft = {
    qty_produced: '',
    waste_qty: '',
    waste_reason: '',
    batch_number: '',
    notes: '',
}

export default function OrdersList() {
    return (
        <ProductionAvailabilityGuard>
            <OrdersListContent />
        </ProductionAvailabilityGuard>
    )
}

function OrdersListContent() {
    const { t } = useTranslation(['productions', 'common'])
    const can = usePermission()
    const features = useResolvedCompanyFeatures()
    const canCreate = can('manufacturing:create')
    const canWrite = can('manufacturing:update') // operar órdenes (start/complete/cancel)
    const canDeleteOrder = can('manufacturing:delete')
    const [items, setItems] = useState<ProductionOrder[]>([])
    const [loading, setLoading] = useState(false)
    const [errMsg, setErrMsg] = useState<string | null>(null)
    const [actionLoadingId, setActionLoadingId] = useState<string | null>(null)
    const [completionTarget, setCompletionTarget] = useState<ProductionOrder | null>(null)
    const [completionDraft, setCompletionDraft] = useState<CompletionDraft>(EMPTY_COMPLETION_DRAFT)
    const [cancelTarget, setCancelTarget] = useState<ProductionOrder | null>(null)
    const [deleteTarget, setDeleteTarget] = useState<ProductionOrder | null>(null)
    const nav = useNavigate()
    const { success, error: toastError } = useToast()
    const [q, setQ] = useState('')

    useEffect(() => {
        void loadOrders()
    }, [])

    const loadOrders = async () => {
        try {
            setLoading(true)
            setItems(await listProductionOrders())
            setErrMsg(null)
        } catch (e: any) {
            const m = getErrorMessage(e)
            setErrMsg(m)
            toastError(m)
        } finally {
            setLoading(false)
        }
    }

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
    const { page, setPage, totalPages, view, setPerPage } = usePagination(sorted, per)
    useEffect(() => setPerPage(per), [per, setPerPage])

    const statusLabel = (s?: string) => {
        const key = s || 'draft'
        const knownStatuses = ['draft', 'scheduled', 'in_progress', 'completed', 'cancelled']
        return knownStatuses.includes(key) ? t(`productions:statuses.${key}`) : s
    }

    const replaceOrder = (next: ProductionOrder) => {
        setItems((prev) => prev.map((item) => item.id === next.id ? next : item))
    }

    const handleStart = async (order: ProductionOrder) => {
        if (!canWrite) return
        try {
            setActionLoadingId(order.id)
            const updated = await startProductionOrder(order.id)
            replaceOrder(updated)
            success(t('productions:messages.started'))
        } catch (e: any) {
            toastError(getErrorMessage(e))
        } finally {
            setActionLoadingId(null)
        }
    }

    const openCompleteModal = (order: ProductionOrder) => {
        if (!canWrite) return
        setCompletionTarget(order)
        setCompletionDraft({
            qty_produced: String(order.qty_planned || ''),
            waste_qty: String(order.waste_qty || ''),
            waste_reason: order.waste_reason || '',
            batch_number: order.batch_number || '',
            notes: '',
        })
    }

    const closeCompleteModal = () => {
        setCompletionTarget(null)
        setCompletionDraft(EMPTY_COMPLETION_DRAFT)
    }

    const handleComplete = async () => {
        if (!canWrite || !completionTarget) return
        const qtyProduced = Number(completionDraft.qty_produced)
        const wasteQty = completionDraft.waste_qty.trim() ? Number(completionDraft.waste_qty) : 0

        if (!qtyProduced || qtyProduced <= 0) {
            toastError(t('productions:messages.qtyProducedRequired'))
            return
        }
        if (Number.isNaN(wasteQty) || wasteQty < 0) {
            toastError(t('productions:messages.wasteQtyInvalid'))
            return
        }

        try {
            setActionLoadingId(completionTarget.id)
            const updated = await completeProductionOrder(completionTarget.id, {
                qty_produced: qtyProduced,
                waste_qty: wasteQty || undefined,
                waste_reason: completionDraft.waste_reason.trim() || undefined,
                batch_number: completionDraft.batch_number.trim() || undefined,
                notes: completionDraft.notes.trim() || undefined,
            })
            replaceOrder(updated)
            closeCompleteModal()
            success(t('productions:messages.completed'))
        } catch (e: any) {
            toastError(getErrorMessage(e))
        } finally {
            setActionLoadingId(null)
        }
    }

    const handleCancel = async (order: ProductionOrder) => {
        if (!canWrite) return
        setCancelTarget(order)
    }

    const doCancel = async () => {
        if (!cancelTarget) return
        const order = cancelTarget
        setCancelTarget(null)
        try {
            setActionLoadingId(order.id)
            const updated = await cancelProductionOrder(order.id)
            replaceOrder(updated)
            success(t('productions:messages.cancelled'))
        } catch (e: any) {
            toastError(getErrorMessage(e))
        } finally {
            setActionLoadingId(null)
        }
    }

    const canStart = (order: ProductionOrder) =>
        order.status === 'draft' || order.status === 'scheduled'

    const canComplete = (order: ProductionOrder) =>
        order.status === 'draft' ||
        order.status === 'scheduled' ||
        order.status === 'in_progress'

    const canCancel = (order: ProductionOrder) =>
        order.status !== 'completed' && order.status !== 'cancelled'

    const canDelete = (order: ProductionOrder) => order.status === 'draft'

    return (
        <div className="p-4">
            <div style={{ marginBottom: '0.75rem' }}><BackButton onClick={() => nav(-1)} /></div>
            <div className="flex justify-between items-center mb-3">
                <h2 className="font-semibold text-lg">{t('productions:title')}</h2>
                <div className="flex items-center gap-2">
                    <button className="px-3 py-1 rounded border" onClick={() => nav('../planificacion')}>
                        {t('productions:planner.open')}
                    </button>
                    {canCreate && (
                        <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={() => nav('nuevo')}>
                            {t('productions:new')}
                        </button>
                    )}
                </div>
            </div>
            <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder={t('productions:searchPlaceholder')}
                className="mb-3 w-full px-3 py-2 border rounded text-sm"
            />
            {loading && <div className="text-sm text-gray-500">{t('productions:loading')}</div>}
            {errMsg && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{errMsg}</div>}
            <div className="flex items-center gap-3 mb-2 text-sm">
                <label>{t('productions:perPage')}</label>
                <select value={per} onChange={(e) => setPer(Number(e.target.value))} className="border px-2 py-1 rounded">
                    <option value={10}>10</option>
                    <option value={25}>25</option>
                    <option value={50}>50</option>
                </select>
            </div>
            <table className="min-w-full text-sm">
                <thead>
                    <tr className="text-left border-b">
                        <th><button className="underline" onClick={() => { setSortKey('numero'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>{t('productions:number')} {sortKey === 'numero' ? (sortDir === 'asc' ? '^' : 'v') : ''}</button></th>
                        <th><button className="underline" onClick={() => { setSortKey('status'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>{t('productions:status')} {sortKey === 'status' ? (sortDir === 'asc' ? '^' : 'v') : ''}</button></th>
                        <th><button className="underline" onClick={() => { setSortKey('scheduled_date'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>{t('productions:date')} {sortKey === 'scheduled_date' ? (sortDir === 'asc' ? '^' : 'v') : ''}</button></th>
                        <th>{t('productions:plannedQty')}</th>
                        <th>{t('productions:producedQty')}</th>
                        <th>{t('productions:actions')}</th>
                    </tr>
                </thead>
                <tbody>
                    {view.map((o) => {
                        const busy = actionLoadingId === o.id
                        return (
                            <tr key={o.id} className="border-b align-top">
                                <td className="py-2 pr-3">
                                    <div>{o.numero || '-'}</div>
                                    {o.batch_number && (
                                        <div className="text-xs text-gray-500">
                                            {t('productions:fields.batch')}: {o.batch_number}
                                        </div>
                                    )}
                                </td>
                                <td className="py-2 pr-3">{statusLabel(o.status)}</td>
                                <td className="py-2 pr-3">{o.scheduled_date || '-'}</td>
                                <td className="py-2 pr-3">{o.qty_planned}</td>
                                <td className="py-2 pr-3">
                                    <div>{o.qty_produced || 0}</div>
                                    {features.production_waste_tracking && (o.waste_qty || 0) > 0 && (
                                        <div className="text-xs text-amber-700">
                                            {t('productions:fields.waste')}: {o.waste_qty}
                                        </div>
                                    )}
                                </td>
                                <td className="py-2">
                                    <div className="flex flex-wrap gap-3">
                                        <Link to={canWrite ? `${o.id}/editar` : `../recetas/${o.recipe_id}`} className="text-blue-600 hover:underline">
                                            {canWrite ? t('productions:edit') : t('recipesList.view', { defaultValue: 'View' })}
                                        </Link>
                                        {canWrite && canStart(o) && (
                                            <button
                                                className="text-emerald-700 disabled:text-gray-400"
                                                disabled={busy}
                                                onClick={() => void handleStart(o)}
                                            >
                                                {t('productions:actionsLabels.start')}
                                            </button>
                                        )}
                                        {canWrite && canComplete(o) && (
                                            <button
                                                className="text-indigo-700 disabled:text-gray-400"
                                                disabled={busy}
                                                onClick={() => openCompleteModal(o)}
                                            >
                                                {t('productions:actionsLabels.complete')}
                                            </button>
                                        )}
                                        {canWrite && canCancel(o) && (
                                            <button
                                                className="text-amber-700 disabled:text-gray-400"
                                                disabled={busy}
                                                onClick={() => void handleCancel(o)}
                                            >
                                                {t('productions:actionsLabels.cancel')}
                                            </button>
                                        )}
                                        {canDeleteOrder && canDelete(o) && (
                                            <button className="text-red-700 disabled:text-gray-400" disabled={busy} onClick={() => setDeleteTarget(o)}>
                                                {t('productions:delete')}
                                            </button>
                                        )}
                                    </div>
                                </td>
                            </tr>
                        )
                    })}
                    {!loading && items.length === 0 && (
                        <tr>
                            <td className="py-3 px-3" colSpan={6}>{t('productions:empty')}</td>
                        </tr>
                    )}
                </tbody>
            </table>
            <Pagination page={page} setPage={setPage} totalPages={totalPages} />

            {canWrite && completionTarget && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-lg p-6 w-full max-w-xl shadow-xl">
                        <h3 className="text-lg font-semibold mb-4">{t('productions:completeModal.title')}</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block mb-1 text-sm font-medium">
                                    {t('productions:completeModal.qtyProduced')}
                                </label>
                                <input
                                    type="number"
                                    min="0.01"
                                    step="0.01"
                                    className="border px-3 py-2 w-full rounded"
                                    value={completionDraft.qty_produced}
                                    onChange={(e) => setCompletionDraft((prev) => ({ ...prev, qty_produced: e.target.value }))}
                                />
                            </div>
                            {features.production_waste_tracking && (
                                <div>
                                    <label className="block mb-1 text-sm font-medium">
                                        {t('productions:completeModal.wasteQty')}
                                    </label>
                                    <input
                                        type="number"
                                        min="0"
                                        step="0.01"
                                        className="border px-3 py-2 w-full rounded"
                                        value={completionDraft.waste_qty}
                                        onChange={(e) => setCompletionDraft((prev) => ({ ...prev, waste_qty: e.target.value }))}
                                    />
                                </div>
                            )}
                            {features.production_batch_tracking && (
                                <div>
                                    <label className="block mb-1 text-sm font-medium">
                                        {t('productions:completeModal.batchNumber')}
                                    </label>
                                    <input
                                        type="text"
                                        className="border px-3 py-2 w-full rounded"
                                        value={completionDraft.batch_number}
                                        onChange={(e) => setCompletionDraft((prev) => ({ ...prev, batch_number: e.target.value }))}
                                        placeholder={t('productions:completeModal.batchPlaceholder')}
                                    />
                                </div>
                            )}
                            {features.production_waste_tracking && (
                                <div className="md:col-span-2">
                                    <label className="block mb-1 text-sm font-medium">
                                        {t('productions:completeModal.wasteReason')}
                                    </label>
                                    <input
                                        type="text"
                                        className="border px-3 py-2 w-full rounded"
                                        value={completionDraft.waste_reason}
                                        onChange={(e) => setCompletionDraft((prev) => ({ ...prev, waste_reason: e.target.value }))}
                                        placeholder={t('productions:completeModal.wasteReasonPlaceholder')}
                                    />
                                </div>
                            )}
                            <div className="md:col-span-2">
                                <label className="block mb-1 text-sm font-medium">
                                    {t('productions:completeModal.notes')}
                                </label>
                                <textarea
                                    className="border px-3 py-2 w-full rounded"
                                    rows={3}
                                    value={completionDraft.notes}
                                    onChange={(e) => setCompletionDraft((prev) => ({ ...prev, notes: e.target.value }))}
                                    placeholder={t('productions:completeModal.notesPlaceholder')}
                                />
                            </div>
                        </div>
                        <div className="flex gap-3 justify-end mt-6">
                            <button
                                onClick={closeCompleteModal}
                                className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
                            >
                                {t('common:cancel')}
                            </button>
                            <button
                                onClick={() => void handleComplete()}
                                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                                disabled={actionLoadingId === completionTarget.id}
                            >
                                {t('productions:actionsLabels.complete')}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {cancelTarget && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setCancelTarget(null)}>
                    <div className="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full mx-4" onClick={e => e.stopPropagation()}>
                        <h3 className="font-bold text-gray-900 mb-2">{t('productions:messages.cancelConfirm')}</h3>
                        <p className="text-sm text-gray-500 mb-2">{cancelTarget.numero}</p>
                        <div className="flex gap-2 justify-end mt-4">
                            <button className="px-4 py-2 border rounded text-sm" onClick={() => setCancelTarget(null)}>{t('common:cancel')}</button>
                            <button className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded text-sm font-semibold" onClick={() => void doCancel()}>{t('productions:actionsLabels.cancel')}</button>
                        </div>
                    </div>
                </div>
            )}

            {deleteTarget && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setDeleteTarget(null)}>
                    <div className="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full mx-4" onClick={e => e.stopPropagation()}>
                        <h3 className="font-bold text-gray-900 mb-2">{t('productions:deleteConfirm')}</h3>
                        <p className="text-sm text-gray-500 mb-2">{deleteTarget.numero}</p>
                        <div className="flex gap-2 justify-end mt-4">
                            <button className="px-4 py-2 border rounded text-sm" onClick={() => setDeleteTarget(null)}>{t('common:cancel')}</button>
                            <button
                                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded text-sm font-semibold"
                                onClick={async () => {
                                    const o = deleteTarget
                                    setDeleteTarget(null)
                                    try {
                                        setActionLoadingId(o.id)
                                        await removeProductionOrder(o.id)
                                        setItems((p) => p.filter(x => x.id !== o.id))
                                        success(t('productions:deleted'))
                                    } catch (e: any) {
                                        toastError(getErrorMessage(e))
                                    } finally {
                                        setActionLoadingId(null)
                                    }
                                }}
                            >{t('productions:delete')}</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
