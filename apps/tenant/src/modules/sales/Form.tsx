import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createVenta, getVenta, updateVenta, type Venta as V, type VentaLinea } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { useTranslation } from 'react-i18next'

type FormT = Omit<V, 'id' | 'cliente_nombre'>

export default function VentaForm() {
    const { id } = useParams()
    const nav = useNavigate()
    const { t } = useTranslation()
    const [form, setForm] = useState<FormT>({
        numero: '',
        fecha: new Date().toISOString().slice(0, 10),
        total: 0,
        subtotal: 0,
        impuesto: 0,
        cliente_id: undefined,
        estado: 'borrador',
        notas: ''
    })
    const [lineas, setLineas] = useState<VentaLinea[]>([])
    const { success, error } = useToast()
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        if (id) {
            setLoading(true)
            getVenta(id)
                .then((x) => {
                    setForm({
                        numero: x.numero || '',
                        fecha: x.fecha,
                        total: x.total,
                        subtotal: x.subtotal || 0,
                        impuesto: x.impuesto || 0,
                        cliente_id: x.cliente_id,
                        estado: x.estado,
                        notas: x.notas || ''
                    })
                    if (x.lineas) setLineas(x.lineas)
                })
                .finally(() => setLoading(false))
        }
    }, [id])

    useEffect(() => {
        const subtotal = lineas.reduce((sum, l) => sum + (l.cantidad * l.precio_unitario * (1 - (l.descuento || 0) / 100)), 0)
        const impuesto = lineas.reduce((sum, l) => {
            const base = l.cantidad * l.precio_unitario * (1 - (l.descuento || 0) / 100)
            return sum + (base * (l.impuesto_tasa || 0) / 100)
        }, 0)
        const total = subtotal + impuesto
        setForm(prev => ({ ...prev, subtotal, impuesto, total }))
    }, [lineas])

    const addLinea = () => {
        setLineas([...lineas, {
            producto_id: '',
            producto_nombre: '',
            cantidad: 1,
            precio_unitario: 0,
            impuesto_tasa: 21,
            descuento: 0
        }])
    }

    const updateLinea = (idx: number, field: keyof VentaLinea, value: any) => {
        const updated = [...lineas]
        updated[idx] = { ...updated[idx], [field]: value }
        setLineas(updated)
    }

    const removeLinea = (idx: number) => {
        setLineas(lineas.filter((_, i) => i !== idx))
    }

    const onSubmit: React.FormEventHandler = async (e) => {
        e.preventDefault()
        try {
            if (!form.fecha) throw new Error(t('sales.errors.dateRequired'))
            if (form.total < 0) throw new Error(t('sales.errors.totalNonNegative'))

            const payload = { ...form, lineas }

            if (id) await updateVenta(id, payload)
            else await createVenta(payload)

            success(t('sales.saved'))
            nav('..')
        } catch (e: any) {
            error(getErrorMessage(e))
        }
    }

    if (loading) return <div className="p-4">{t('common.loading')}</div>

    return (
        <div className="p-4">
            <button className="mb-3 underline text-sm" onClick={() => nav('..')}>? {t('common.back')}</button>
            <h3 className="text-xl font-semibold mb-3">{id ? t('sales.editSale') : t('sales.newSale')}</h3>

            <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 920 }}>
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block mb-1 text-sm font-medium">{t('sales.saleNumber')}</label>
                        <input
                            value={form.numero}
                            onChange={(e) => setForm({ ...form, numero: e.target.value })}
                            className="border px-2 py-1 w-full rounded"
                            placeholder={t('sales.numberPlaceholder')}
                        />
                    </div>
                    <div>
                        <label className="block mb-1 text-sm font-medium">{t('common.date')}</label>
                        <input
                            type="date"
                            value={form.fecha}
                            onChange={(e) => setForm({ ...form, fecha: e.target.value })}
                            className="border px-2 py-1 w-full rounded"
                            required
                        />
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block mb-1 text-sm font-medium">{t('sales.customerId')}</label>
                        <input
                            type="number"
                            value={form.cliente_id ?? ''}
                            onChange={(e) => setForm({ ...form, cliente_id: e.target.value ? Number(e.target.value) : undefined })}
                            className="border px-2 py-1 w-full rounded"
                            placeholder={t('common.optional')}
                        />
                        <small className="text-gray-500">{t('sales.integrateCustomerSelector')}</small>
                    </div>
                    <div>
                        <label className="block mb-1 text-sm font-medium">{t('common.status')}</label>
                        <select
                            value={form.estado || 'borrador'}
                            onChange={(e) => setForm({ ...form, estado: e.target.value })}
                            className="border px-2 py-1 w-full rounded"
                        >
                            <option value="borrador">{t('sales.draft')}</option>
                            <option value="emitida">{t('sales.issued')}</option>
                            <option value="anulada">{t('sales.voided')}</option>
                        </select>
                    </div>
                </div>

                <div>
                    <label className="block mb-1 text-sm font-medium">{t('common.notes')}</label>
                    <textarea
                        value={form.notas || ''}
                        onChange={(e) => setForm({ ...form, notas: e.target.value })}
                        className="border px-2 py-1 w-full rounded"
                        rows={3}
                        placeholder={t('common.notesPlaceholder')}
                    />
                </div>

                <div className="border-t pt-4">
                    <div className="flex justify-between items-center mb-3">
                        <h4 className="font-semibold">{t('sales.lines')}</h4>
                        <button
                            type="button"
                            onClick={addLinea}
                            className="bg-green-600 text-white px-3 py-1 rounded text-sm"
                        >
                            + {t('sales.addLine')}
                        </button>
                    </div>

                    {lineas.length === 0 && (
                        <p className="text-sm text-gray-500">{t('sales.noLines')}</p>
                    )}

                    {lineas.map((linea, idx) => (
                        <div key={idx} className="border rounded p-3 mb-3 bg-gray-50">
                            <div className="grid grid-cols-5 gap-2 mb-2">
                                <div>
                                    <label className="text-xs">{t('sales.fields.productId')}</label>
                                    <input
                                        value={linea.producto_id}
                                        onChange={(e) => updateLinea(idx, 'producto_id', e.target.value)}
                                        className="border px-2 py-1 w-full rounded text-sm"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs">{t('common.quantity')}</label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        value={linea.cantidad}
                                        onChange={(e) => updateLinea(idx, 'cantidad', Number(e.target.value))}
                                        className="border px-2 py-1 w-full rounded text-sm"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs">{t('sales.fields.unitPrice')}</label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        value={linea.precio_unitario}
                                        onChange={(e) => updateLinea(idx, 'precio_unitario', Number(e.target.value))}
                                        className="border px-2 py-1 w-full rounded text-sm"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs">{t('sales.fields.taxPercent')}</label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        value={linea.impuesto_tasa || 0}
                                        onChange={(e) => updateLinea(idx, 'impuesto_tasa', Number(e.target.value))}
                                        className="border px-2 py-1 w-full rounded text-sm"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs">{t('sales.fields.discountPercent')}</label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        value={linea.descuento || 0}
                                        onChange={(e) => updateLinea(idx, 'descuento', Number(e.target.value))}
                                        className="border px-2 py-1 w-full rounded text-sm"
                                    />
                                </div>
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-sm">
                                    {t('sales.lineTotal')}: <strong>${((linea.cantidad * linea.precio_unitario * (1 - (linea.descuento || 0) / 100)) + (linea.cantidad * linea.precio_unitario * (1 - (linea.descuento || 0) / 100) * (linea.impuesto_tasa || 0) / 100)).toFixed(2)}</strong>
                                </span>
                                <button
                                    type="button"
                                    onClick={() => removeLinea(idx)}
                                    className="text-red-700 text-sm hover:underline"
                                >
                                    {t('common.delete')}
                                </button>
                            </div>
                        </div>
                    ))}
                </div>

                <div className="border-t pt-4 bg-gray-100 p-3 rounded">
                    <div className="flex justify-between text-sm mb-1">
                        <span>{t('sales.subtotal')}:</span>
                        <span className="font-semibold">${(form.subtotal ?? 0).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between text-sm mb-1">
                        <span>{t('sales.taxes')}:</span>
                        <span className="font-semibold">${(form.impuesto ?? 0).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between text-lg font-bold border-t pt-2">
                        <span>{t('common.total')}:</span>
                        <span className="text-blue-700">${form.total.toFixed(2)}</span>
                    </div>
                </div>

                <div className="pt-2 flex gap-3">
                    <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded font-medium">
                        {t('common.save')}
                    </button>
                    <button type="button" className="bg-gray-200 px-4 py-2 rounded" onClick={() => nav('..')}>
                        {t('common.cancel')}
                    </button>
                </div>
            </form>
        </div>
    )
}
