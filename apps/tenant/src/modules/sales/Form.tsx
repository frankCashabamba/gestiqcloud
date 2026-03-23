import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createVenta, getVenta, updateVenta, isPosReadOnly, type Venta as V, type VentaLinea } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { useTranslation } from 'react-i18next'
import { usePermission } from '../../hooks/usePermission'
import { useCompanyConfig } from '../../contexts/CompanyConfigContext'
import PermissionDenied from '../../components/PermissionDenied'
import ProtectedButton from '../../components/ProtectedButton'
import ProductLineRow from './components/ProductLineRow'
import RecipePicker from './components/RecipePicker'
import CustomerSelector from './components/CustomerSelector'

const SPECIAL_ORDER_SECTORS = new Set(['panaderia', 'panaderia_pro', 'taller', 'taller_pro'])

type FormT = Omit<V, 'id' | 'cliente_nombre'>

export default function VentaForm() {
    const { id } = useParams()
    const nav = useNavigate()
    const { t } = useTranslation()
    const can = usePermission()
    const { config } = useCompanyConfig()
    const sector = config?.sector?.plantilla || ''
    const isSpecialOrder = SPECIAL_ORDER_SECTORS.has(sector)
    const requiredPerm = id ? 'sales:update' : 'sales:create'
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
    const [deliveryDate, setDeliveryDate] = useState('')
    const [depositAmount, setDepositAmount] = useState(0)
    const [depositPaid, setDepositPaid] = useState(false)
    const [paymentMethod, setPaymentMethod] = useState('')
    const [lineas, setLineas] = useState<VentaLinea[]>([])
    const [showPicker, setShowPicker] = useState(false)
    const [clienteName, setClienteName] = useState('')
    const [posReadOnly, setPosReadOnly] = useState(false)
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
                    if (x.cliente_nombre) setClienteName(x.cliente_nombre)
                    setPosReadOnly(isPosReadOnly(x))
                    if (x.delivery_date) setDeliveryDate(x.delivery_date)
                    if (x.deposit_amount) setDepositAmount(x.deposit_amount)
                    setDepositPaid(x.deposit_paid ?? false)
                    setPaymentMethod(x.payment_method ?? '')
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

    const addLinea = (linea?: Partial<VentaLinea>) => {
        const pid = linea?.producto_id
        if (pid) {
            setLineas(prev => {
                const idx = prev.findIndex(l => String(l.producto_id) === String(pid))
                if (idx !== -1) {
                    const updated = [...prev]
                    updated[idx] = { ...updated[idx], cantidad: updated[idx].cantidad + (linea?.cantidad ?? 1) }
                    return updated
                }
                return [...prev, {
                    producto_id: pid,
                    producto_nombre: linea?.producto_nombre ?? '',
                    cantidad: linea?.cantidad ?? 1,
                    precio_unitario: linea?.precio_unitario ?? 0,
                    impuesto_tasa: linea?.impuesto_tasa ?? 0,
                    descuento: linea?.descuento ?? 0,
                }]
            })
        } else {
            setLineas(prev => [...prev, {
                producto_id: '',
                producto_nombre: '',
                cantidad: 1,
                precio_unitario: 0,
                impuesto_tasa: 0,
                descuento: 0,
            }])
        }
    }

    const updateLinea = (idx: number, field: keyof VentaLinea, value: any) => {
        setLineas(prev => {
            const updated = [...prev]
            updated[idx] = { ...updated[idx], [field]: value }
            return updated
        })
    }

    const removeLinea = (idx: number) => {
        setLineas(prev => prev.filter((_, i) => i !== idx))
    }

    const onSubmit: React.FormEventHandler = async (e) => {
        e.preventDefault()
        try {
            if (!form.fecha) throw new Error(t('sales.errors.dateRequired'))
            if (form.total < 0) throw new Error(t('sales.errors.totalNonNegative'))

            const payload: any = { ...form, lineas }
            if (isSpecialOrder) {
                payload.delivery_date = deliveryDate || undefined
                payload.deposit_amount = depositAmount
                payload.deposit_paid = depositPaid
                payload.payment_method = paymentMethod || undefined
            }

            if (id) await updateVenta(id, payload)
            else await createVenta(payload)

            success(t('sales.saved'))
            nav('..')
        } catch (e: any) {
            error(getErrorMessage(e))
        }
    }

    if (!can(requiredPerm)) {
        return <PermissionDenied permission={requiredPerm} />
    }

    if (loading) return <div className="p-4">{t('common.loading')}</div>

    if (posReadOnly) {
        return (
            <div className="p-4">
                <button className="mb-3 underline text-sm" onClick={() => nav('..')}>← {t('common.back')}</button>
                <div className="bg-amber-50 border border-amber-300 rounded-lg p-4 text-amber-800">
                    <p className="font-semibold mb-1">{t('sales.posReadOnlyTitle')}</p>
                    <p className="text-sm">{t('sales.posReadOnlyBody')}</p>
                </div>
            </div>
        )
    }

    return (
        <div className="p-4">
            <button className="mb-3 underline text-sm" onClick={() => nav('..')}>← {t('common.back')}</button>
            <h3 className="text-xl font-semibold mb-3">{id ? t('sales.editSale') : t('sales.newSale')}</h3>

            <form onSubmit={onSubmit} className="space-y-4 max-w-4xl">
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="gc-label">{t('sales.saleNumber')}</label>
                        <input
                            value={form.numero}
                            onChange={(e) => setForm({ ...form, numero: e.target.value })}
                            className="gc-input"
                            placeholder={t('sales.numberPlaceholder')}
                        />
                    </div>
                    <div>
                        <label className="gc-label">{t('common.date')}</label>
                        <input
                            type="date"
                            value={form.fecha}
                            onChange={(e) => setForm({ ...form, fecha: e.target.value })}
                            className="gc-input"
                            required
                        />
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="gc-label">{t('sales.customer')}</label>
                        <CustomerSelector
                            value={form.cliente_id}
                            clienteName={clienteName}
                            onChange={(id, name) => {
                                setForm(prev => ({ ...prev, cliente_id: id }))
                                setClienteName(name)
                            }}
                        />
                    </div>
                    <div>
                        <label className="gc-label">{t('common.status')}</label>
                        <select
                            value={form.estado || 'borrador'}
                            onChange={(e) => setForm({ ...form, estado: e.target.value })}
                            className="gc-input"
                        >
                            <option value="borrador">{t('sales.draft')}</option>
                            <option value="emitida">{t('sales.issued')}</option>
                            <option value="anulada">{t('sales.voided')}</option>
                        </select>
                    </div>
                </div>

                <div>
                    <label className="gc-label">{t('common.notes')}</label>
                    <textarea
                        value={form.notas || ''}
                        onChange={(e) => setForm({ ...form, notas: e.target.value })}
                        className="gc-input"
                        rows={3}
                        placeholder={t('common.notesPlaceholder')}
                    />
                </div>

                {isSpecialOrder && (
                    <div className="border rounded-lg p-4 bg-amber-50 border-amber-200">
                        <h4 className="font-semibold mb-3 text-amber-800">
                            {sector.startsWith('taller') ? t('sales.specialOrder.titleTaller') : t('sales.specialOrder.titlePanaderia')}
                        </h4>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="gc-label">
                                    {sector.startsWith('taller') ? t('sales.specialOrder.deliveryDateTaller') : t('sales.specialOrder.deliveryDatePanaderia')}
                                </label>
                                <input
                                    type="date"
                                    value={deliveryDate}
                                    onChange={(e) => setDeliveryDate(e.target.value)}
                                    className="gc-input"
                                />
                            </div>
                            <div>
                                <label className="gc-label">{t('sales.specialOrder.deposit')}</label>
                                <input
                                    type="number"
                                    min="0"
                                    step="0.01"
                                    value={depositAmount}
                                    onChange={(e) => setDepositAmount(Number(e.target.value))}
                                    className="gc-input"
                                />
                            </div>
                            <div>
                                <label className="gc-label">{t('sales.specialOrder.paymentMethod')}</label>
                                <select
                                    value={paymentMethod}
                                    onChange={(e) => setPaymentMethod(e.target.value)}
                                    className="gc-input"
                                >
                                    <option value="">{t('sales.specialOrder.noDeposit')}</option>
                                    <option value="efectivo">{t('sales.specialOrder.cash')}</option>
                                    <option value="transferencia">{t('sales.specialOrder.transfer')}</option>
                                    <option value="tarjeta">{t('sales.specialOrder.card')}</option>
                                    <option value="whatsapp">{t('sales.specialOrder.whatsapp')}</option>
                                </select>
                            </div>
                            <div className="flex items-center gap-2 pt-6">
                                <input
                                    id="deposit-paid"
                                    type="checkbox"
                                    checked={depositPaid}
                                    onChange={(e) => setDepositPaid(e.target.checked)}
                                    className="w-4 h-4"
                                />
                                <label htmlFor="deposit-paid" className="cursor-pointer text-sm font-medium">
                                    {t('sales.specialOrder.depositPaid')}
                                </label>
                            </div>
                        </div>
                        {(form.total ?? 0) > 0 && depositAmount > 0 && (
                            <p className="mt-3 text-sm font-medium text-amber-700">
                                {t('sales.specialOrder.pendingBalance', { amount: ((form.total ?? 0) - depositAmount).toFixed(2) })}
                            </p>
                        )}
                    </div>
                )}

                <div className="border-t pt-4">
                    <div className="flex justify-between items-center mb-3">
                        <h4 className="font-semibold">{t('sales.lines')}</h4>
                        {can(requiredPerm) && !showPicker && (
                            <ProtectedButton
                                permission={requiredPerm}
                                type="button"
                                variant="primary"
                                onClick={() => setShowPicker(true)}
                            >
                                + {t('sales.addLine')}
                            </ProtectedButton>
                        )}
                    </div>

                    {showPicker && (
                        <RecipePicker
                            currentLines={lineas}
                            onAdd={(l) => addLinea(l)}
                            onClose={() => setShowPicker(false)}
                        />
                    )}

                    {lineas.length === 0 && !showPicker && (
                        <p className="text-sm text-slate-500">{t('sales.noLines')}</p>
                    )}

                    {lineas.map((linea, idx) => (
                        <ProductLineRow
                            key={idx}
                            idx={idx}
                            linea={linea}
                            onUpdate={updateLinea}
                            onRemove={removeLinea}
                        />
                    ))}
                </div>

                <div className="border-t pt-4 bg-slate-100 p-3 rounded">
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
                    {can(requiredPerm) && (
                        <ProtectedButton
                            permission={requiredPerm}
                            type="submit"
                            variant="primary"
                            className="px-4 py-2 font-medium"
                        >
                            {t('common.save')}
                        </ProtectedButton>
                    )}
                    <button type="button" className="bg-slate-200 px-4 py-2 rounded" onClick={() => nav('..')}>
                        {t('common.cancel')}
                    </button>
                </div>
            </form>
        </div>
    )
}
