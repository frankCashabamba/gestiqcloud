import React, { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { getVenta, removeVenta, isPosReadOnly, checkoutOrder, type Venta } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import StatusBadge from './components/StatusBadge'

export default function VentaDetail() {
    const { id } = useParams<{ id: string }>()
    const nav = useNavigate()
    const { t } = useTranslation()
    const [venta, setVenta] = useState<Venta | null>(null)
    const [loading, setLoading] = useState(true)
    const [checkingOut, setCheckingOut] = useState(false)
    const [confirmDelete, setConfirmDelete] = useState(false)
    const { success, error } = useToast()

    useEffect(() => {
        if (!id) return
        getVenta(id).then((v) => setVenta(v)).catch((e) => error(getErrorMessage(e))).finally(() => setLoading(false))
    }, [id])

    const handleDelete = async () => {
        if (!id) return
        setConfirmDelete(false)
        try {
            await removeVenta(id)
            success(t('sales.deleted'))
            nav('..')
        } catch (e: any) {
            error(getErrorMessage(e))
        }
    }

    const handleCheckout = async () => {
        if (!id) return
        setCheckingOut(true)
        try {
            const result = await checkoutOrder(id)
            success(result.message)
            if (result.expense_note) {
                error(t('sales.expenseNote', { note: result.expense_note }))
            }
            // Recargar para reflejar estado 'invoiced'
            getVenta(id).then(setVenta).catch(() => {})
        } catch (e: any) {
            error(getErrorMessage(e))
        } finally {
            setCheckingOut(false)
        }
    }

    if (loading) return <div className="p-4">{t('common.loading')}</div>
    if (!venta) return <div className="p-4">{t('errors.notFound')}</div>

    return (
        <div className="p-4" style={{ maxWidth: 840 }}>
            <button className="mb-3 underline text-sm" onClick={() => nav('..')}>← {t('common.back')}</button>

            <div className="flex justify-between items-start mb-4">
                <div>
                    <h2 className="text-2xl font-semibold">{t('sales.saleNumber')}{venta.numero || venta.id}</h2>
                    <p className="text-sm text-gray-600">ID: {venta.id}</p>
                </div>
                <StatusBadge estado={venta.estado} />
            </div>

            <div className="bg-white border rounded-lg p-4 mb-4">
                <h3 className="font-semibold mb-3 text-lg">{t('sales.title')}</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <label className="text-gray-600">{t('sales.saleNumber')}:</label>
                        <p className="font-medium">{venta.numero || '-'}</p>
                    </div>
                    <div>
                        <label className="text-gray-600">{t('common.date')}:</label>
                        <p className="font-medium">{venta.fecha}</p>
                    </div>
                    <div>
                        <label className="text-gray-600">{t('sales.customer')}:</label>
                        <p className="font-medium">{venta.cliente_nombre || (venta.cliente_id ? `ID: ${venta.cliente_id}` : '—')}</p>
                    </div>
                    <div>
                        <label className="text-gray-600">{t('common.status')}:</label>
                        <p className="font-medium">{venta.estado || '-'}</p>
                    </div>
                    {venta.notas && (
                        <div className="col-span-2">
                            <label className="text-gray-600">{t('common.notes')}:</label>
                            <p className="font-medium">{venta.notas}</p>
                        </div>
                    )}
                </div>
            </div>

            {venta.lineas && venta.lineas.length > 0 && (
                <div className="bg-white border rounded-lg p-4 mb-4">
                    <h3 className="font-semibold mb-3 text-lg">{t('sales.lines')}</h3>
                    <table className="min-w-full text-sm">
                        <thead>
                            <tr className="border-b">
                                <th className="text-left py-2">{t('common.name')}</th>
                                <th className="text-right py-2">{t('common.quantity')}</th>
                                <th className="text-right py-2">{t('common.price')}</th>
                                <th className="text-right py-2">{t('sales.fields.discountPercent')}</th>
                                <th className="text-right py-2">{t('sales.fields.taxPercent')}</th>
                                <th className="text-right py-2">{t('common.total')}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {venta.lineas.map((linea, idx) => {
                                const base = linea.cantidad * linea.precio_unitario * (1 - (linea.descuento || 0) / 100)
                                const impuesto = base * (linea.impuesto_tasa || 0) / 100
                                const total = base + impuesto
                                return (
                                    <tr key={idx} className="border-b">
                                        <td className="py-2">{linea.producto_nombre || `ID: ${linea.producto_id}`}</td>
                                        <td className="text-right py-2">{linea.cantidad}</td>
                                        <td className="text-right py-2">${linea.precio_unitario.toFixed(2)}</td>
                                        <td className="text-right py-2">{linea.descuento || 0}%</td>
                                        <td className="text-right py-2">{linea.impuesto_tasa || 0}%</td>
                                        <td className="text-right py-2 font-semibold">${total.toFixed(2)}</td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            )}

            <div className="bg-gray-100 border rounded-lg p-4 mb-4">
                <h3 className="font-semibold mb-3 text-lg">{t('common.total')}</h3>
                <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                        <span>{t('sales.subtotal')}:</span>
                        <span className="font-semibold">${(venta.subtotal || 0).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                        <span>{t('sales.taxes')}:</span>
                        <span className="font-semibold">${(venta.impuesto || 0).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between text-lg font-bold border-t pt-2">
                        <span>{t('common.total')}:</span>
                        <span className="text-blue-700">${venta.total.toFixed(2)}</span>
                    </div>
                </div>
            </div>

            <div className="bg-white border rounded-lg p-4">
                <h3 className="font-semibold mb-3 text-lg">{t('common.actions')}</h3>
                <div className="flex gap-3 flex-wrap">
                    {!isPosReadOnly(venta) && (
                        <Link
                            to={`../${venta.id}/edit`}
                            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                        >
                            {t('common.edit')}
                        </Link>
                    )}

                    {!['anulada', 'facturada'].includes(venta.estado ?? '') && venta.estado !== 'invoiced' && (
                        <button
                            onClick={handleCheckout}
                            disabled={checkingOut}
                            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
                        >
                            {checkingOut ? t('common.loading') : t('sales.invoice')}
                        </button>
                    )}

                    {!isPosReadOnly(venta) && (
                        <button
                            onClick={() => setConfirmDelete(true)}
                            className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
                        >
                            {t('common.delete')}
                        </button>
                    )}

                    <button
                        onClick={() => window.print()}
                        className="bg-gray-200 px-4 py-2 rounded hover:bg-gray-300"
                    >
                        {t('common.print')}
                    </button>
                </div>
            </div>

            {venta.created_at && (
                <div className="mt-4 text-xs text-gray-500">
                    {t('common.create')}: {new Date(venta.created_at).toLocaleString()}
                    {venta.updated_at && ` • ${t('common.update')}: ${new Date(venta.updated_at).toLocaleString()}`}
                </div>
            )}

            {confirmDelete && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setConfirmDelete(false)}>
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
                                onClick={() => setConfirmDelete(false)}
                            >
                                {t('common.cancel')}
                            </button>
                            <button
                                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-sm font-semibold transition-colors"
                                onClick={() => void handleDelete()}
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
