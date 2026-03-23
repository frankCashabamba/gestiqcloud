import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { createGasto, getGasto, updateGasto, type Gasto } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { useCompanySector } from '../../contexts/CompanyConfigContext'
import { useExpenseCategories } from '../../hooks/useGlobalCatalogs'
import { useSectorPlaceholders, getFieldPlaceholder } from '../../hooks/useSectorPlaceholders'

type FormT = Omit<Gasto, 'id' | 'created_at' | 'updated_at'>

const CATEGORIAS_FALLBACK = [
  'Rent',
  'Services',
  'Personnel',
  'Marketing',
  'Supplies',
  'Transport',
  'Taxes',
  'Maintenance',
  'Other',
]

const SUBCATEGORIAS: Record<string, string[]> = {
  'Services': ['Electricity', 'Water', 'Internet', 'Phone', 'Gas'],
  'Personnel': ['Salaries', 'Social Security', 'Bonuses', 'Meals'],
  'Marketing': ['Advertising', 'Social Media', 'Events', 'Promotional Materials'],
  'Supplies': ['Office', 'Cleaning', 'Packaging', 'Materials'],
  'Transport': ['Fuel', 'Vehicle Maintenance', 'Tolls', 'Parking'],
}

export default function GastoForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const { t } = useTranslation(['expenses', 'common'])
  const { success, error } = useToast()
  const sector = useCompanySector()
  const { placeholders } = useSectorPlaceholders(sector?.plantilla, 'expenses')
  const { items: expenseCategories, loading: loadingCats } = useExpenseCategories()
  const categorias = !loadingCats && expenseCategories.length > 0
    ? expenseCategories.map((c) => c.name)
    : !loadingCats
    ? CATEGORIAS_FALLBACK
    : []

  const [form, setForm] = useState<FormT>({
    date: new Date().toISOString().slice(0, 10),
    category: '',
    subcategory: '',
    concept: '',
    amount: 0,
    payment_method: 'cash',
    supplier_id: '',
    supplier_name: '',
    status: 'pending',
    invoice_number: '',
    notes: '',
  })

  const [loading, setLoading] = useState(false)

  const isLockedProductionExpense = (expense: Gasto) =>
    expense.category === 'production' || String(expense.invoice_number || '').startsWith('PROD-')

  useEffect(() => {
    if (id) {
      setLoading(true)
      getGasto(id)
        .then((x) => {
          if (isLockedProductionExpense(x)) {
            throw new Error(t('expenses:form.errors.lockedProduction', 'Los gastos de producción son generados por el sistema y no se pueden editar'))
          }
          setForm({
            date: x.date,
            category: x.category,
            subcategory: x.subcategory || '',
            concept: x.concept || '',
            amount: x.amount,
            payment_method: x.payment_method || 'cash',
            supplier_id: x.supplier_id || '',
            supplier_name: x.supplier_name || '',
            status: x.status || 'pending',
            invoice_number: x.invoice_number || '',
            notes: x.notes || '',
          })
        })
        .catch((e) => {
          error(getErrorMessage(e))
          nav('..')
        })
        .finally(() => setLoading(false))
    }
  }, [id])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.date) throw new Error(t('expenses:form.errors.dateRequired'))
      if (!form.category) throw new Error(t('expenses:form.errors.categoryRequired'))
      if (!form.concept) throw new Error(t('expenses:form.errors.conceptRequired'))
      if (form.amount <= 0) throw new Error(t('expenses:form.errors.amountPositive'))

      setLoading(true)
      if (id) {
        await updateGasto(id, form)
      } else {
        await createGasto(form as Omit<Gasto, 'id'>)
      }
      success(t('expenses:messages.saved'))
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  // Si la categoría guardada no está en la lista (ej: 'production'), añadirla para no perder el valor
  const allCategorias = form.category && !categorias.includes(form.category)
    ? [form.category, ...categorias]
    : categorias

  const subcategorias = form.category ? (SUBCATEGORIAS[form.category] || []) : []

  return (
    <div className="gc-container py-6">
      <h3 className="text-xl font-semibold mb-6">
        {id ? t('expenses:form.titleEdit') : t('expenses:form.title')}
      </h3>

      <form onSubmit={onSubmit} className="space-y-4 max-w-3xl">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="gc-label">{t('expenses:form.date')} *</label>
            <input
              type="date"
              value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
              className="gc-input"
              required
              disabled={loading}
            />
          </div>

          <div>
            <label className="gc-label">{t('expenses:form.amount')} *</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={form.amount}
              onChange={(e) => setForm({ ...form, amount: Number(e.target.value) })}
              className="gc-input"
              required
              disabled={loading}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="gc-label">{t('expenses:form.category')} *</label>
            <select
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value, subcategory: '' })}
              className="gc-input"
              required
              disabled={loading}
            >
              <option value="">{t('expenses:form.selectCategory')}</option>
              {allCategorias.map((cat) => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>

          {subcategorias.length > 0 && (
            <div>
              <label className="gc-label">{t('expenses:form.subcategory')}</label>
              <select
                value={form.subcategory || ''}
                onChange={(e) => setForm({ ...form, subcategory: e.target.value })}
                className="gc-input"
                disabled={loading}
              >
                <option value="">{t('expenses:form.selectSubcategory')}</option>
                {subcategorias.map((sub) => (
                  <option key={sub} value={sub}>{sub}</option>
                ))}
              </select>
            </div>
          )}
        </div>

        <div>
          <label className="gc-label">{t('expenses:form.concept')} *</label>
          <input
            type="text"
            placeholder={t('expenses:form.conceptPlaceholder')}
            value={form.concept}
            onChange={(e) => setForm({ ...form, concept: e.target.value })}
            className="gc-input"
            required
            disabled={loading}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="gc-label">{t('expenses:form.paymentMethod')} *</label>
            <select
              value={form.payment_method}
              onChange={(e) => setForm({ ...form, payment_method: e.target.value as any })}
              className="gc-input"
              required
              disabled={loading}
            >
              <option value="cash">{t('expenses:paymentMethods.cash')}</option>
              <option value="transfer">{t('expenses:paymentMethods.transfer')}</option>
              <option value="card">{t('expenses:paymentMethods.card')}</option>
              <option value="check">{t('expenses:paymentMethods.check')}</option>
            </select>
          </div>

          <div>
            <label className="gc-label">{t('expenses:form.status')} *</label>
            <select
              value={form.status}
              onChange={(e) => setForm({ ...form, status: e.target.value as any })}
              className="gc-input"
              required
              disabled={loading}
            >
              <option value="pending">{t('expenses:statuses.pending')}</option>
              <option value="paid">{t('expenses:statuses.paid')}</option>
              <option value="voided">{t('expenses:statuses.voided')}</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="gc-label">{t('expenses:form.supplierId')}</label>
            <input
              type="text"
              placeholder={t('expenses:form.supplierIdPlaceholder')}
              value={form.supplier_id || ''}
              onChange={(e) => setForm({ ...form, supplier_id: e.target.value })}
              className="gc-input"
              disabled={loading}
            />
          </div>

          <div>
            <label className="gc-label">{t('expenses:form.supplierName')}</label>
            <input
              type="text"
              placeholder={t('expenses:form.supplierNamePlaceholder')}
              value={form.supplier_name || ''}
              onChange={(e) => setForm({ ...form, supplier_name: e.target.value })}
              className="gc-input"
              disabled={loading}
            />
          </div>
        </div>

        <div>
          <label className="gc-label">{t('expenses:form.invoiceNumber')}</label>
          <input
            type="text"
            placeholder={getFieldPlaceholder(placeholders, 'invoice_number', 'Ej: INV-2025-001')}
            value={form.invoice_number || ''}
            onChange={(e) => setForm({ ...form, invoice_number: e.target.value })}
            className="gc-input"
            disabled={loading}
          />
        </div>

        <div>
          <label className="gc-label">{t('expenses:form.notes')}</label>
          <textarea
            value={form.notes || ''}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            className="gc-input"
            rows={3}
            placeholder={t('expenses:form.notesPlaceholder')}
            disabled={loading}
          />
        </div>

        <div className="pt-2 flex gap-3 border-t">
          <button
            type="submit"
            className="gc-btn gc-btn--primary disabled:opacity-50"
            disabled={loading}
          >
            {loading ? t('expenses:form.saving') : t('expenses:form.save')}
          </button>
          <button
            type="button"
            className="gc-btn gc-btn--ghost"
            onClick={() => nav('..')}
            disabled={loading}
          >
            {t('common:cancel')}
          </button>
        </div>
      </form>
    </div>
  )
}
