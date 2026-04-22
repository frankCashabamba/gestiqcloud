import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { createPurchase, getPurchase, updatePurchase, type Purchase } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import PurchaseLinesEditor from './components/PurchaseLinesEditor'
import { getCompanySettings, getDefaultTaxRate } from '../../services/companySettings'
import { PURCHASING_DEFAULTS } from '../../constants/defaults'
import { usePermission } from '../../hooks/usePermission'
import PermissionDenied from '../../components/PermissionDenied'
import ProtectedButton from '../../components/ProtectedButton'

type FormT = Omit<Purchase, 'id' | 'created_at' | 'updated_at'>

export default function PurchaseForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const { t } = useTranslation(['purchases', 'common'])
  const { success, error } = useToast()
  const can = usePermission()
  const requiredPerm = id ? 'purchases:update' : 'purchases:create'

  const [form, setForm] = useState<FormT>({
    date: new Date().toISOString().slice(0, 10),
    delivery_date: '',
    supplier_id: '',
    supplier_name: '',
    subtotal: 0,
    taxes: 0,
    total: 0,
    status: 'draft',
    lines: [],
    notes: '',
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
    if (!id) return
    setLoading(true)
    getPurchase(id)
      .then((x) => {
        setForm({
          number: x.number,
          date: x.date,
          delivery_date: x.delivery_date || '',
          supplier_id: x.supplier_id || '',
          supplier_name: x.supplier_name || '',
          subtotal: x.subtotal,
          taxes: x.taxes,
          total: x.total,
          status: x.status,
          lines: x.lines || [],
          notes: x.notes || '',
        })
      })
      .catch((e) => error(getErrorMessage(e)))
      .finally(() => setLoading(false))
  }, [id, error])

  useEffect(() => {
    const subtotal = (form.lines || []).reduce((sum, line) => sum + line.subtotal, 0)
    const taxes = subtotal * taxRate
    const total = subtotal + taxes

    setForm((prev) => ({
      ...prev,
      subtotal,
      taxes,
      total,
    }))
  }, [form.lines, taxRate])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()

    try {
      if (!form.date) throw new Error(t('purchases:form.dateRequired'))
      if (!form.lines || form.lines.length === 0) {
        throw new Error(t('purchases:form.linesRequired'))
      }
      if (form.total < 0) throw new Error(t('purchases:form.totalPositive'))

      setLoading(true)

      if (id) {
        await updatePurchase(id, form)
      } else {
        await createPurchase(form as Omit<Purchase, 'id'>)
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
      <h3 className="text-xl font-semibold mb-3">
        {id ? t('purchases:edit') : t('purchases:new')}
      </h3>

      <form onSubmit={onSubmit} className="space-y-4 max-w-4xl">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block mb-1 font-medium">{t('purchases:date')} *</label>
            <input
              type="date"
              value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
              className="border px-2 py-1 w-full rounded"
              required
              disabled={loading}
            />
          </div>

          <div>
            <label className="block mb-1 font-medium">{t('purchases:form.deliveryDate')}</label>
            <input
              type="date"
              value={form.delivery_date || ''}
              onChange={(e) => setForm({ ...form, delivery_date: e.target.value })}
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
              value={form.supplier_id || ''}
              onChange={(e) => setForm({ ...form, supplier_id: e.target.value })}
              className="border px-2 py-1 w-full rounded"
              disabled={loading}
            />
          </div>

          <div>
            <label className="block mb-1 font-medium">{t('purchases:form.supplierName')}</label>
            <input
              type="text"
              placeholder={t('purchases:form.supplierName')}
              value={form.supplier_name || ''}
              onChange={(e) => setForm({ ...form, supplier_name: e.target.value })}
              className="border px-2 py-1 w-full rounded"
              disabled={loading}
            />
          </div>
        </div>

        <div>
          <label className="block mb-1 font-medium">{t('purchases:status')}</label>
          <select
            value={form.status}
            onChange={(e) => setForm({ ...form, status: e.target.value as any })}
            className="border px-2 py-1 w-full rounded"
            disabled={loading}
          >
            <option value="draft">{t('purchases:draft')}</option>
            <option value="sent">{t('purchases:sent')}</option>
            <option value="received">{t('purchases:received')}</option>
            <option value="cancelled">{t('purchases:cancelled')}</option>
          </select>
        </div>

        <PurchaseLinesEditor
          lines={form.lines || []}
          onChange={(lines) => setForm({ ...form, lines })}
        />

        <div className="bg-gray-50 p-4 rounded space-y-2">
          <div className="flex justify-between text-sm">
            <span>{t('purchases:detail.subtotal')}:</span>
            <span className="font-medium">
              {form.subtotal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span>{t('purchases:form.tax', { rate: (taxRate * 100).toFixed(2) })}:</span>
            <span className="font-medium">
              {form.taxes.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          <div className="flex justify-between text-lg font-bold border-t pt-2">
            <span>{t('purchases:total')}:</span>
            <span>{form.total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
          </div>
        </div>

        <div>
          <label className="block mb-1 font-medium">{t('purchases:form.notes')}</label>
          <textarea
            value={form.notes || ''}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
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
