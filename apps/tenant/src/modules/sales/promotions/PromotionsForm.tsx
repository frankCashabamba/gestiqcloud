import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useToast, getErrorMessage } from '../../../shared/toast'
import {
  createPromotion,
  updatePromotion,
  type Promotion,
  type PromotionIn,
} from './promotionsService'

type Props = {
  initial: Promotion | null
  onSaved: (p: Promotion) => void
  onClose: () => void
}

const EMPTY: PromotionIn = {
  name: '',
  description: '',
  type: 'percentage',
  value: 0,
  valid_from: '',
  valid_to: '',
  min_purchase: 0,
  applies_to: 'all',
  product_ids: [],
  promo_code: '',
  is_active: true,
  usage_limit: undefined,
}

export default function PromotionsForm({ initial, onSaved, onClose }: Props) {
  const { t } = useTranslation()
  const { error: toastError } = useToast()
  const isEdit = !!initial

  const [form, setForm] = useState<PromotionIn>(() => {
    if (!initial) return { ...EMPTY }
    return {
      name: initial.name,
      description: initial.description ?? '',
      type: initial.type,
      value: initial.value,
      valid_from: initial.valid_from ?? '',
      valid_to: initial.valid_to ?? '',
      min_purchase: initial.min_purchase,
      applies_to: initial.applies_to,
      product_ids: initial.product_ids ?? [],
      promo_code: initial.promo_code ?? '',
      is_active: initial.is_active,
      usage_limit: initial.usage_limit,
    }
  })
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  function set<K extends keyof PromotionIn>(key: K, value: PromotionIn[K]) {
    setForm(prev => ({ ...prev, [key]: value }))
    setErrors(prev => { const n = { ...prev }; delete n[key as string]; return n })
  }

  function validate(): boolean {
    const e: Record<string, string> = {}
    if (!form.name.trim()) e.name = t('promotions.errorNameRequired')
    if (form.value < 0) e.value = t('promotions.errorValueNegative')
    if (form.type === 'percentage' && form.value > 100) e.value = t('promotions.errorPctMax')
    if (form.valid_from && form.valid_to && form.valid_from > form.valid_to)
      e.valid_to = t('promotions.errorDateRange')
    if (form.usage_limit !== undefined && form.usage_limit !== null && form.usage_limit < 1)
      e.usage_limit = t('promotions.errorUsageLimitMin')
    setErrors(e)
    return Object.keys(e).length === 0
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!validate()) return
    setSaving(true)
    const payload: PromotionIn = {
      ...form,
      promo_code: form.promo_code?.trim().toUpperCase() || undefined,
      description: form.description?.trim() || undefined,
      valid_from: form.valid_from || undefined,
      valid_to: form.valid_to || undefined,
      product_ids: form.product_ids?.length ? form.product_ids : undefined,
      usage_limit: form.usage_limit || undefined,
    }
    try {
      const saved = isEdit
        ? await updatePromotion(initial!.id, payload)
        : await createPromotion(payload)
      onSaved(saved)
    } catch (err: any) {
      toastError(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b">
          <h2 className="font-semibold text-lg text-slate-900">
            {isEdit ? t('promotions.editTitle') : t('promotions.newTitle')}
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 transition-colors"
            aria-label={t('common.close')}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={e => void handleSubmit(e)} className="px-6 py-5 space-y-4">
          {/* Nombre */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              {t('promotions.fieldName')} <span className="text-red-500">*</span>
            </label>
            <input
              value={form.name}
              onChange={e => set('name', e.target.value)}
              className={`w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.name ? 'border-red-400' : 'border-slate-300'}`}
              placeholder={t('promotions.fieldNamePlaceholder')}
            />
            {errors.name && <p className="text-xs text-red-500 mt-1">{errors.name}</p>}
          </div>

          {/* Descripción */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              {t('promotions.fieldDescription')}
            </label>
            <textarea
              value={form.description ?? ''}
              onChange={e => set('description', e.target.value)}
              rows={2}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>

          {/* Tipo + Valor */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                {t('promotions.fieldType')}
              </label>
              <select
                value={form.type}
                onChange={e => set('type', e.target.value as any)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="percentage">{t('promotions.type.percentage')}</option>
                <option value="fixed">{t('promotions.type.fixed')}</option>
                <option value="bogo">{t('promotions.type.bogo')}</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                {t('promotions.fieldValue')}
                {form.type === 'percentage' && ' (%)'}
                {form.type === 'fixed' && ' ($)'}
              </label>
              <input
                type="number"
                min={0}
                max={form.type === 'percentage' ? 100 : undefined}
                step="0.01"
                value={form.value}
                onChange={e => set('value', parseFloat(e.target.value) || 0)}
                disabled={form.type === 'bogo'}
                className={`w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-50 disabled:text-slate-400 ${errors.value ? 'border-red-400' : 'border-slate-300'}`}
              />
              {errors.value && <p className="text-xs text-red-500 mt-1">{errors.value}</p>}
            </div>
          </div>

          {/* Vigencia */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                {t('promotions.fieldValidFrom')}
              </label>
              <input
                type="date"
                value={form.valid_from ?? ''}
                onChange={e => set('valid_from', e.target.value || undefined)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                {t('promotions.fieldValidTo')}
              </label>
              <input
                type="date"
                value={form.valid_to ?? ''}
                onChange={e => set('valid_to', e.target.value || undefined)}
                className={`w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.valid_to ? 'border-red-400' : 'border-slate-300'}`}
              />
              {errors.valid_to && <p className="text-xs text-red-500 mt-1">{errors.valid_to}</p>}
            </div>
          </div>

          {/* Compra mínima + Código */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                {t('promotions.fieldMinPurchase')}
              </label>
              <input
                type="number"
                min={0}
                step="0.01"
                value={form.min_purchase}
                onChange={e => set('min_purchase', parseFloat(e.target.value) || 0)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                {t('promotions.fieldPromoCode')}
              </label>
              <input
                value={form.promo_code ?? ''}
                onChange={e => set('promo_code', e.target.value.toUpperCase())}
                placeholder="ej. VERANO25"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 uppercase"
              />
            </div>
          </div>

          {/* Límite de uso */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              {t('promotions.fieldUsageLimit')}
            </label>
            <input
              type="number"
              min={1}
              step={1}
              value={form.usage_limit ?? ''}
              onChange={e => set('usage_limit', e.target.value ? parseInt(e.target.value) : undefined)}
              placeholder={t('promotions.fieldUsageLimitPlaceholder')}
              className={`w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.usage_limit ? 'border-red-400' : 'border-slate-300'}`}
            />
            {errors.usage_limit && <p className="text-xs text-red-500 mt-1">{errors.usage_limit}</p>}
          </div>

          {/* Estado activo */}
          <div className="flex items-center gap-3 pt-1">
            <button
              type="button"
              role="switch"
              aria-checked={form.is_active}
              onClick={() => set('is_active', !form.is_active)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 ${form.is_active ? 'bg-blue-600' : 'bg-slate-300'}`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${form.is_active ? 'translate-x-6' : 'translate-x-1'}`}
              />
            </button>
            <span className="text-sm text-slate-700">
              {form.is_active ? t('promotions.activeOn') : t('promotions.activeOff')}
            </span>
          </div>

          {/* Acciones */}
          <div className="flex justify-end gap-2 pt-2 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-slate-200 rounded-xl text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
            >
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-semibold transition-colors disabled:opacity-50"
            >
              {saving ? '...' : isEdit ? t('common.save') : t('promotions.create')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
