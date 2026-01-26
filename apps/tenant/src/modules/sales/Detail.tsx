import React, { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { getVenta, removeVenta, type Venta } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import StatusBadge from './components/StatusBadge'

export default function VentaDetail() {
    const { id } = useParams()
    const nav = useNavigate()
    const { t } = useTranslation()
    const [venta, setVenta] = useState<Venta | null>(null)
    const [loading, setLoading] = useState(true)
    const { success, error } = useToast()

    useEffect(() => {
        if (!id) return
        getVenta(id).then((v) => setVenta(v)).catch((e) => error(getErrorMessage(e))).finally(() => setLoading(false))
    }, [id])

    const handleDelete = async () => {
        if (!id || !confirm('Delete this sale permanently?')) return
        try {
            await removeVenta(id)
            success('Sale deleted')
            nav('..')
        } catch (e: any) {
            error(getErrorMessage(e))
        }
    }

    const handleConvertToInvoice = () => {
        // Navegar a facturación con pre-fill de datos
        nav(`/invoicing/new?from_sale=${id}`)
    }

    if (loading) return <div className="p-4">{t('common.loading')}</div>
    if (!venta) return <div className="p-4">{t('errors.notFound')}</div>

    return (
        <div className="p-4" style={{ maxWidth: 840 }}>
            <button className="mb-3 underline text-sm" onClick={() => nav('..')}>← {t('common.back')} to {t('nav.sales')}</button>

            <div className="flex justify-between items-start mb-4">
                <div>
                    <h2 className="text-2xl font-semibold">{t('sales.saleNumber')}{venta.numero || venta.id}</h2>
                    <p className="text-sm text-gray-600">ID: {venta.id}</p>
                </div>
                <StatusBadge estado={venta.estado} />
            </div>

            <div className="bg-white border rounded-lg p-4 mb-4">
                <h3 className="font-semibold mb-3 text-lg">{t('sales.title')} {t('common.info')}</h3>
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
                        <p className="font-medium">{venta.cliente_nombre || `ID: ${venta.cliente_id}` || t('common.noRecords')}</p>
                    </div>
                    <div>
                        <label className="text-gray-600">{t('common.status')}:</label>
                        <p className="font-medium">{venta.estado || '-'}</p>
                    </div>
                    {venta.notas && (
                        <div className="col-span-2">
                            <label className="text-gray-600">{t('billing.fields.notes')}:</label>
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
                    <Link
                        to={`../${venta.id}/editar`}
                        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                    >
                        {t('common.edit')}
                    </Link>

                    {venta.estado === 'borrador' && (
                        <button
                            onClick={handleConvertToInvoice}
                            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                        >
                            {t('sales.invoice')}
                        </button>
                    )}

                    <button
                        onClick={handleDelete}
                        className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
                    >
                        {t('common.delete')}
                    </button>

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
        </div>
    )
}
