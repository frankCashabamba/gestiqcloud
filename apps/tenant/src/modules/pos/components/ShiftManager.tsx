/**
 * ShiftManager - Gestión de turnos de caja
 */
import React, { useState, useEffect, useImperativeHandle } from 'react'
import { useTranslation } from 'react-i18next'
import { openShift, closeShift, getCurrentShift, getShiftSummary, getLastDailyCount } from '../services'
import type { POSShift, POSRegister, ShiftSummary } from '../../../types/pos'
import { useCurrency } from '../../../hooks/useCurrency'
import { POS_DEFAULTS } from '../../../constants/defaults'
import { useToast } from '../../../shared/toast'
import { useAuth } from '../../../auth/AuthContext'
import { usePermission } from '../../../hooks/usePermission'

interface ShiftManagerProps {
    register: POSRegister
    onShiftChange: (shift: POSShift | null) => void
    compact?: boolean
}

export interface ShiftManagerHandle {
    openCloseModal: () => void
}

const ShiftManager = React.forwardRef<ShiftManagerHandle, ShiftManagerProps>(
    ({ register, onShiftChange, compact = false }, ref) => {
        const { t } = useTranslation(['pos', 'common'])
        const { symbol: currencySymbol, formatCurrency } = useCurrency()
        const toast = useToast()
        const { profile } = useAuth()
        const can = usePermission()
        const [currentShift, setCurrentShift] = useState<POSShift | null>(null)
        const [loading, setLoading] = useState(false)
        const [openingFloat, setOpeningFloat] = useState(POS_DEFAULTS.OPENING_FLOAT)
        const [closingCash, setClosingCash] = useState('')
        const [lossAmount, setLossAmount] = useState('')
        const [lossNote, setLossNote] = useState('')
        const [showCloseModal, setShowCloseModal] = useState(false)
        const [summary, setSummary] = useState<ShiftSummary | null>(null)
        const [loadingSummary, setLoadingSummary] = useState(false)
        const canEditClose =
            !!(profile?.es_admin_empresa || (profile as any)?.is_company_admin) ||
            can('pos:update') ||
            can('pos:write')
        const parseMoney = (raw: string) => {
            if (!raw) return 0
            const normalized = raw.replace(',', '.').trim()
            const num = Number.parseFloat(normalized)
            return Number.isFinite(num) ? num : 0
        }
        const closingCashValue = parseMoney(closingCash)
        const lossAmountValue = parseMoney(lossAmount)
        const netCashToSave = Math.max(0, closingCashValue - lossAmountValue)

        useEffect(() => {
            loadCurrentShift()
            loadSuggestedOpeningFloat()
        }, [register.id])

        const loadCurrentShift = async () => {
            try {
                const shift = await getCurrentShift(register.id)
                setCurrentShift(shift)
                onShiftChange(shift)
            } catch (error) {
                console.error('Error loading shift:', error)
            }
        }

        const loadSuggestedOpeningFloat = async () => {
            try {
                const lastCount = await getLastDailyCount(register.id)
                if (lastCount && lastCount.counted_cash > 0) {
                    setOpeningFloat(lastCount.counted_cash.toFixed(2))
                }
            } catch (error) {
                console.error('Error loading suggested opening float:', error)
            }
        }

        const handleOpenShift = async () => {
            if (!openingFloat || parseFloat(openingFloat) < 0) {
                toast.warning(t('pos:shiftManager.validOpeningAmount'))
                return
            }

            setLoading(true)
            try {
                const shift = await openShift({
                    register_id: register.id,
                    opening_float: parseFloat(openingFloat)
                })
                setCurrentShift(shift)
                onShiftChange(shift)
                toast.success(t('pos:shiftManager.openedSuccess'))
            } catch (error: any) {
                toast.error(error.response?.data?.detail || t('pos:shiftManager.errorOpening'))
            } finally {
                setLoading(false)
            }
        }

        const handleShowCloseModal = async () => {
            setShowCloseModal(true)
            if (currentShift) {
                setLoadingSummary(true)
                try {
                    const shiftSummary = await getShiftSummary(currentShift.id)
                    setSummary(shiftSummary)
                    const cashTotal = shiftSummary.payments?.cash || shiftSummary.payments?.efectivo || 0
                    if (cashTotal > 0) {
                        setClosingCash(cashTotal.toFixed(2))
                    }
                } catch (error: any) {
                    console.error('Error loading summary:', error)
                    toast.error(t('pos:shiftManager.errorLoadingSummary'))
                } finally {
                    setLoadingSummary(false)
                }
            }
        }

        useImperativeHandle(ref, () => ({
            openCloseModal: () => {
                if (!currentShift) return
                void handleShowCloseModal()
            }
        }), [currentShift])

        const handleCloseShift = async () => {
            if (!currentShift) return

            if (summary && summary.pending_receipts > 0) {
                toast.warning(t('pos:shiftManager.cannotClosePending', { count: summary.pending_receipts }))
                return
            }

            if (!closingCash || parseFloat(closingCash) < 0) {
                toast.warning(t('pos:shiftManager.enterCashTotal'))
                return
            }

            setLoading(true)
            try {
                const payload: any = {
                    shift_id: currentShift.id,
                    closing_cash: parseFloat(closingCash),
                }

                if (lossAmount && parseFloat(lossAmount) > 0) {
                    payload.loss_amount = parseFloat(lossAmount)
                }
                if (lossNote) {
                    payload.loss_note = lossNote
                }

                const result = await closeShift(payload)

                const discrepancy = result.difference
                const msg = `${t('pos:shiftManager.closedSuccess')}\n\n` +
                    `${t('pos:shiftManager.totalSalesLabel')}: ${formatCurrency(result.total_sales || 0)}\n` +
                    `${t('pos:shiftManager.cashSalesLabel')}: ${formatCurrency(result.cash_sales || 0)}\n` +
                    `${t('pos:shiftManager.expectedCash')}: ${formatCurrency(result.expected_cash || 0)}\n` +
                    `${t('pos:shiftManager.countedCash')}: ${formatCurrency(result.counted_cash || 0)}\n` +
                    `${t('pos:shiftManager.differenceLabel')}: ${formatCurrency(discrepancy || 0)}` +
                    (result.loss_amount > 0 ? `\n${t('pos:shiftManager.lossesAmount')}: ${formatCurrency(result.loss_amount || 0)}` : '') +
                    (result.loss_note ? `\n${t('pos:shiftManager.noteLabel')}: ${result.loss_note}` : '')

                toast.success(msg)

                setCurrentShift(null)
                onShiftChange(null)
                setShowCloseModal(false)
                setClosingCash('')
                setLossAmount('')
                setLossNote('')
                setSummary(null)
            } catch (error: any) {
                toast.error(error.response?.data?.detail || t('pos:shiftManager.errorClosing'))
            } finally {
                setLoading(false)
            }
        }

        if (!currentShift) {
            return (
                <div className="bg-white rounded-lg shadow p-6 mb-4">
                    <h2 className="text-xl font-bold mb-4">{t('pos:shiftManager.openShiftTitle', { name: register.name })}</h2>
                    <div className="mb-4">
                        <label className="block text-sm font-medium mb-2">
                            {t('pos:shiftManager.openingAmount')} ({currencySymbol})
                            <span className="text-xs text-gray-500 ml-2">{t('pos:shiftManager.suggestedFromPrevious')}</span>
                        </label>
                        <input
                            type="number"
                            step="0.01"
                            value={openingFloat}
                            onChange={(e) => setOpeningFloat(e.target.value)}
                            className="w-full px-3 py-2 border border-slate-300 rounded bg-white text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            disabled={loading}
                        />
                    </div>
                    <button
                        onClick={handleOpenShift}
                        disabled={loading}
                        className="bg-green-600 text-white px-6 py-2 rounded hover:bg-green-700 disabled:opacity-50"
                    >
                        {loading ? t('pos:shiftManager.opening') : t('pos:shiftManager.openShift')}
                    </button>
                </div>
            )
        }

        return (
            <>
                {!compact && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4 flex justify-between items-center">
                        <div>
                            <h3 className="font-semibold text-green-800">{t('pos:shiftManager.shiftOpen')}</h3>
                            <p className="text-sm text-green-700">
                                {t('pos:shiftManager.openedAt')}: {new Date(currentShift.opened_at).toLocaleString()} |
                                {t('pos:shiftManager.fund')}: {currencySymbol}{(Number(currentShift.opening_float) || 0).toFixed(2)}
                            </p>
                        </div>
                        <button
                            onClick={handleShowCloseModal}
                            className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
                        >
                            {t('pos:shiftManager.closeShift')}
                        </button>
                    </div>
                )}

                {showCloseModal && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto">
                        <div className="bg-white rounded-lg p-6 max-w-4xl w-full m-4 max-h-[90vh] overflow-y-auto">
                            <div className="flex items-start justify-between mb-3">
                                <div>
                                    <p className="text-xs uppercase tracking-wide text-gray-500 font-semibold">{t('pos:shiftManager.closeShift')}</p>
                                    <h3 className="text-2xl font-bold text-gray-900">{t('pos:shiftManager.summaryAndClose')}</h3>
                                    <p className="text-sm text-gray-600">{t('pos:shiftManager.reviewDescription')}</p>
                                </div>
                                <button
                                    onClick={() => setShowCloseModal(false)}
                                    className="text-gray-400 hover:text-gray-600 text-lg font-bold px-2"
                                    aria-label={t('pos:shiftManager.closeModal')}
                                >
                                    ×
                                </button>
                            </div>

                            {loadingSummary ? (
                                <div className="py-8 text-center text-gray-500">{t('pos:shiftManager.loadingSummary')}</div>
                            ) : summary ? (
                                <>
                                    {/* Alertas */}
                                    {summary.pending_receipts > 0 && (
                                        <div className="bg-red-50 border border-red-300 text-red-800 p-3 rounded mb-4">
                                            {t('pos:shiftManager.pendingReceiptsWarning', { count: summary.pending_receipts })}
                                        </div>
                                    )}

                                    {/* Resumen de ventas */}
                                    <div className="mb-4 p-4 bg-blue-50 rounded border border-blue-100">
                                        <h4 className="font-semibold mb-1 text-blue-900">{t('pos:shiftManager.salesSummary')}</h4>
                                        <p className="text-sm text-blue-900">{t('pos:shiftManager.totalSales')}: {formatCurrency(summary.sales_total)}</p>
                                        <p className="text-sm text-blue-900">{t('pos:shiftManager.productsCount')}: {summary.receipts_count}</p>
                                    </div>

                                    {/* Productos vendidos */}
                                    <div className="mb-4">
                                        <div className="flex items-center justify-between mb-2">
                                            <h4 className="font-semibold text-gray-900">{t('pos:shiftManager.productsSold')}</h4>
                                            <span className="text-xs text-gray-500">{t('pos:shiftManager.remainingStock')}</span>
                                        </div>
                                        <div className="max-h-60 overflow-y-auto border rounded shadow-sm bg-white">
                                            <table className="w-full text-[14px] text-slate-800">
                                                <thead className="bg-slate-100 sticky top-0 text-slate-800 border-b border-slate-300 shadow-sm">
                                                    <tr>
                                                        <th className="p-2 text-left font-semibold">{t('pos:shiftManager.code')}</th>
                                                        <th className="p-2 text-left font-semibold">{t('pos:shiftManager.product')}</th>
                                                        <th className="p-2 text-right font-semibold">{t('pos:shiftManager.sold')}</th>
                                                        <th className="p-2 text-right font-semibold">{t('pos:shiftManager.subtotal')}</th>
                                                        <th className="p-2 text-right font-semibold">{t('pos:shiftManager.remainingStockCol')}</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {summary.items_sold
                                                        .filter(item => item.qty_sold > 0)
                                                        .map((item, idx) => (
                                                            <tr key={idx} className="border-t border-slate-200 odd:bg-white even:bg-slate-50">
                                                                <td className="p-2 text-slate-700">{item.code || '-'}</td>
                                                                <td className="p-2 text-slate-900 font-medium">{item.name}</td>
                                                                <td className="p-2 text-right text-slate-800">{item.qty_sold.toFixed(2)}</td>
                                                                <td className="p-2 text-right text-slate-900 font-semibold">{formatCurrency(item.subtotal)}</td>
                                                                <td className="p-2 text-right text-slate-700">
                                                                    {item.stock.length > 0 ? (
                                                                        <div className="space-y-1">
                                                                            {item.stock.map((s, i) => (
                                                                                <div key={i} className={s.qty < 0 ? 'text-red-600 font-semibold' : s.qty === 0 ? 'text-slate-400' : 'text-slate-700'}>
                                                                                    {s.warehouse_name}: {s.qty.toFixed(2)}
                                                                                </div>
                                                                            ))}
                                                                        </div>
                                                                    ) : (
                                                                        <span className="text-slate-400">-</span>
                                                                    )}
                                                                </td>
                                                            </tr>
                                                        ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </>
                            ) : null}

                            {/* Formulario de cierre */}
                            <div className="space-y-4 border-t border-slate-200 pt-4 mt-4">
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
                                    <div className="min-w-0">
                                        <div className="flex items-center justify-between mb-1">
                                            <label className="block text-sm font-semibold text-slate-800">{t('pos:shiftManager.cashTotal')} ({currencySymbol})</label>
                                            {summary?.payments && (
                                                <div className="text-xs text-slate-600 space-x-2 text-right leading-tight">
                                                    <span>{t('pos:shiftManager.registeredCash')}: {formatCurrency(summary.payments?.cash || summary.payments?.efectivo || 0)}</span>
                                                    {summary.payments?.card ? <span>{t('pos:shiftManager.cardLabel')}: {formatCurrency(summary.payments.card)}</span> : null}
                                                    {summary.payments?.link ? <span>{t('pos:shiftManager.linkLabel')}: {formatCurrency(summary.payments.link)}</span> : null}
                                                    {summary.payments?.store_credit ? <span>{t('pos:shiftManager.creditLabel')}: {formatCurrency(summary.payments.store_credit)}</span> : null}
                                                </div>
                                            )}
                                        </div>
                                        <input
                                            type="number"
                                            step="0.01"
                                            inputMode="decimal"
                                            value={closingCash}
                                            onChange={(e) => setClosingCash(e.target.value)}
                                            className="w-full px-3 py-2 border border-slate-300 rounded bg-white text-slate-900 text-right font-semibold placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                            placeholder="0.00"
                                            autoFocus
                                            disabled={!canEditClose}
                                        />
                                    </div>

                                    <div className="min-w-0">
                                        <label className="block text-sm font-semibold text-slate-800 mb-2">{t('pos:shiftManager.lossesLabel')} ({currencySymbol})</label>
                                        <input
                                            type="number"
                                            step="0.01"
                                            inputMode="decimal"
                                            value={lossAmount}
                                            onChange={(e) => setLossAmount(e.target.value)}
                                            className="w-full px-3 py-2 border border-slate-300 rounded bg-white text-slate-900 text-right font-semibold placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                            placeholder="0.00"
                                            disabled={!canEditClose}
                                        />
                                        <p className="mt-1 text-xs text-slate-500">
                                            {t('pos:shiftManager.lossesHint')}
                                        </p>
                                    </div>

                                    <div className="min-w-0">
                                        <label className="block text-sm font-semibold text-slate-800 mb-2">{t('pos:shiftManager.totalToSave')} ({currencySymbol})</label>
                                        <input
                                            type="text"
                                            value={formatCurrency(netCashToSave)}
                                            className="w-full px-3 py-2 border border-emerald-300 rounded bg-emerald-50 text-emerald-800 text-right font-bold"
                                            readOnly
                                            aria-label={t('pos:shiftManager.totalToSave')}
                                        />
                                        <p className="mt-1 text-xs text-slate-500">
                                            {t('pos:shiftManager.autoCalculated')}
                                        </p>
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-semibold text-slate-800 mb-2">{t('pos:shiftManager.lossNote')}</label>
                                    <textarea
                                        value={lossNote}
                                        onChange={(e) => setLossNote(e.target.value)}
                                        className="w-full px-3 py-2 border border-slate-300 rounded bg-white text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        placeholder={t('pos:shiftManager.lossPlaceholder')}
                                        rows={3}
                                        disabled={!canEditClose}
                                    />
                                    {!canEditClose && (
                                        <p className="mt-1 text-xs text-amber-700">
                                            {t('pos:shiftManager.noEditPermission')}
                                        </p>
                                    )}
                                </div>
                            </div>

                            <div className="flex gap-2 mt-6">
                                <button
                                    onClick={handleCloseShift}
                                    disabled={loading || (summary?.pending_receipts ?? 0) > 0}
                                    className="flex-1 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {loading ? t('pos:shiftManager.closing') : t('pos:shiftManager.closeCash')}
                                </button>
                                <button
                                    onClick={() => {
                                        setShowCloseModal(false)
                                        setSummary(null)
                                    }}
                                    disabled={loading}
                                    className="flex-1 bg-slate-200 text-slate-800 px-4 py-2 rounded hover:bg-slate-300 font-medium"
                                >
                                    {t('pos:shiftManager.cancel')}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </>
        )
    }
)

ShiftManager.displayName = 'ShiftManager'

export default ShiftManager