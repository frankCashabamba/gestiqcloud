import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { createCompra, getCompra, updateCompra, type Compra, type CompraLinea } from './services'
import { BackButton } from '@ui'
import { useToast, getErrorMessage } from '../../shared/toast'
import CompraLineasEditor from './components/CompraLineasEditor'
import { getCompanySettings, getDefaultTaxRate } from '../../services/companySettings'
import { PURCHASING_DEFAULTS } from '../../constants/defaults'
import { usePermission } from '../../hooks/usePermission'
import PermissionDenied from '../../components/PermissionDenied'
import ProtectedButton from '../../components/ProtectedButton'

type FormT = Omit<Compra, 'id' | 'created_at' | 'updated_at'>

export default function CompraForm() {
    const { id } = useParams()
    const nav = useNavigate()
    const { t } = useTranslation(['purchases', 'common'])
    const { success, error } = useToast()
    const can = usePermission()
    const requiredPerm = id ? 'purchases:update' : 'purchases:create'

    const [form, setForm] = useState<FormT>({
        fecha: new Date().toISOString().slice(0, 10),
        fecha_entrega: '',
        proveedor_id: '',
        proveedor_nombre: '',
        subtotal: 0,
        impuesto: 0,
        total: 0,
        estado: 'draft',
        lineas: [],
        notas: ''
    })

    const [loading, setLoading] = useState(false)
    const [taxRate, setTaxRate] = useState(PURCHASING_DEFAULTS.TAX_RATE)

    useEffect(() => {
        let cancelled = false
        const loadTaxRate = async () => {
            try {
                const settings = await getCompanySettings()
                const rate = getDefaultTaxRate(settings, 0)
                if (!cancelled) setTaxRate(Number.isFinite(rate) ? rate : 0)
            } catch {
                if (!cancelled) setTaxRate(0)
            }
        }
        loadTaxRate()
        return () => {
            cancelled = true
        }
    }, [])


    useEffect(() => {
        if (id) {
            setLoading(true)
            getCompra(id)
                .then((x) => {
                    setForm({
                        numero: x.numero,
                        fecha: x.fecha,
                        fecha_entrega: x.fecha_entrega || '',
                        proveedor_id: x.proveedor_id || '',
                        proveedor_nombre: x.proveedor_nombre || '',
                        subtotal: x.subtotal,
                        impuesto: x.impuesto,
                        total: x.total,
                        estado: x.estado,
                        lineas: x.lineas || [],
                        notas: x.notas || ''
                    })
                })
                .catch((e) => error(getErrorMessage(e)))
                .finally(() => setLoading(false))
        }
    }, [id])

    useEffect(() => {
        // Recalcular totales cuando cambian las líneas
        const subtotal = (form.lineas || []).reduce((sum, l) => sum + l.subtotal, 0)
        const impuesto = subtotal * taxRate
        const total = subtotal + impuesto

        setForm(prev => ({
            ...prev,
            subtotal,
            impuesto,
            total
        }))
    }, [form.lineas, taxRate])

    const onSubmit: React.FormEventHandler = async (e) => {
        e.preventDefault()

        try {
            if (!form.fecha) throw new Error(t('purchases:form.dateRequired'))
            if (!form.lineas || form.lineas.length === 0) {
                throw new Error(t('purchases:form.linesRequired'))
            }
            if (form.total < 0) throw new Error(t('purchases:form.totalPositive'))

            setLoading(true)

            if (id) {
                await updateCompra(id, form)
            } else {
                await createCompra(form as Omit<Compra, 'id'>)
            }

            success(t('purchases:saved'))
            nav('..')
        } catch (e: any) {
            error(getErrorMessage(e))
        } finally {
            setLoading(false)
        }
    }

    if (!can(requiredPerm)) {
        return <PermissionDenied permission={requiredPerm} />
    }

    return (
        <div className="p-4">
            <div style={{ marginBottom: '0.75rem' }}><BackButton onClick={() => nav(-1)} /></div>
            <h3 className="text-xl font-semibold mb-3">
                {id ? t('purchases:edit') : t('purchases:new')}
            </h3>

            <form onSubmit={onSubmit} className="space-y-4 max-w-4xl">
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block mb-1 font-medium">{t('purchases:date')} *</label>
                        <input
                            type="date"
                            value={form.fecha}
                            onChange={(e) => setForm({ ...form, fecha: e.target.value })}
                            className="border px-2 py-1 w-full rounded"
                            required
                            disabled={loading}
                        />
                    </div>

                    <div>
                        <label className="block mb-1 font-medium">{t('purchases:form.deliveryDate')}</label>
                        <input
                            type="date"
                            value={form.fecha_entrega || ''}
                            onChange={(e) => setForm({ ...form, fecha_entrega: e.target.value })}
                            className="border px-2 py-1 w-full rounded"
                            disabled={loading}
                        />
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block mb-1 font-medium">{t('purchases:form.supplierId')}</label>
                        <input
                            type="text"
                            placeholder={t('purchases:form.supplierId')}
                            value={form.proveedor_id || ''}
                            onChange={(e) => setForm({ ...form, proveedor_id: e.target.value })}
                            className="border px-2 py-1 w-full rounded"
                            disabled={loading}
                        />
                    </div>

                    <div>
                        <label className="block mb-1 font-medium">{t('purchases:form.supplierName')}</label>
                        <input
                            type="text"
                            placeholder={t('purchases:form.supplierName')}
                            value={form.proveedor_nombre || ''}
                            onChange={(e) => setForm({ ...form, proveedor_nombre: e.target.value })}
                            className="border px-2 py-1 w-full rounded"
                            disabled={loading}
                        />
                    </div>
                </div>

                <div>
                    <label className="block mb-1 font-medium">{t('purchases:status')}</label>
                    <select
                        value={form.estado}
                        onChange={(e) => setForm({ ...form, estado: e.target.value as any })}
                        className="border px-2 py-1 w-full rounded"
                        disabled={loading}
                    >
                        <option value="draft">{t('purchases:draft')}</option>
                        <option value="sent">{t('purchases:sent')}</option>
                        <option value="received">{t('purchases:received')}</option>
                        <option value="cancelled">{t('purchases:cancelled')}</option>
                    </select>
                </div>

                <CompraLineasEditor
                    lineas={form.lineas || []}
                    onChange={(lineas) => setForm({ ...form, lineas })}
                />

                <div className="bg-gray-50 p-4 rounded space-y-2">
                    <div className="flex justify-between text-sm">
                        <span>{t('purchases:detail.subtotal')}:</span>
                        <span className="font-medium">{form.subtotal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                        <span>{t('purchases:form.tax', { rate: (taxRate * 100).toFixed(2) })}:</span>
                        <span className="font-medium">{form.impuesto.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </div>
                    <div className="flex justify-between text-lg font-bold border-t pt-2">
                        <span>{t('purchases:total')}:</span>
                        <span>{form.total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </div>
                </div>

                <div>
                    <label className="block mb-1 font-medium">{t('purchases:form.notes')}</label>
                    <textarea
                        value={form.notas || ''}
                        onChange={(e) => setForm({ ...form, notas: e.target.value })}
                        className="border px-2 py-1 w-full rounded"
                        rows={3}
                        placeholder={t('purchases:form.notesPlaceholder')}
                        disabled={loading}
                    />
                </div>

                <div className="pt-2 flex gap-3">
                    <ProtectedButton
                        permission={requiredPerm}
                        type="submit"
                        variant="primary"
                        className="px-4 py-2 font-medium"
                        disabled={loading}
                    >
                        {loading ? t('purchases:form.saving') : t('purchases:form.save')}
                    </ProtectedButton>
                    <button
                        type="button"
                        className="px-4 py-2 border rounded hover:bg-gray-50"
                        onClick={() => nav('..')}
                        disabled={loading}
                    >
                        {t('purchases:form.cancel')}
                    </button>
                </div>
            </form>
        </div>
    )
}
