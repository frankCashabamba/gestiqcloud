import React, { useEffect, useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useToast } from '../../shared/toast'
import {
  getReceiptSettings,
  saveReceiptSettings,
  getReceiptPreview,
  type ReceiptConfig,
} from '../../services/api/printing'
import { getCompanySettings, updateCompanySettings } from '../../services/companySettings'

export default function ReceiptTemplateSettings() {
  const { t } = useTranslation(['settings', 'common'])
  const { error: showError } = useToast()
  const [config, setConfig] = useState<ReceiptConfig>({
    footer_message: t('settings:receipt.defaultFooter'),
    show_tax_breakdown: true,
    show_cashier: true,
    show_customer: true,
    custom_header: '',
    custom_footer: '',
  })
  const [paperWidthMm, setPaperWidthMm] = useState<number | ''>(80)
  const [preview, setPreview] = useState('')
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    let cancelled = false
    Promise.all([
      getReceiptSettings().catch(() => null),
      getCompanySettings({ force: true }).catch(() => null),
    ]).then(([receiptData, settingsData]) => {
      if (cancelled) return
      if (receiptData) setConfig((prev) => ({ ...prev, ...receiptData }))
      const w = settingsData?.pos_config?.receipt?.width_mm
      if (w != null && Number.isFinite(Number(w))) setPaperWidthMm(Number(w))
    })
    return () => { cancelled = true }
  }, [])

  const refreshPreview = useCallback(() => {
    let cancelled = false
    setLoadingPreview(true)
    getReceiptPreview()
      .then((data) => { if (!cancelled) setPreview(data.preview || '') })
      .catch(() => { if (!cancelled) setPreview('') })
      .finally(() => { if (!cancelled) setLoadingPreview(false) })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    return refreshPreview()
  }, [refreshPreview])

  const handleChange = (field: keyof ReceiptConfig, value: string | boolean) => {
    setConfig((prev) => ({ ...prev, [field]: value }))
    setSaved(false)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await Promise.all([
        saveReceiptSettings(config),
        paperWidthMm !== ''
          ? updateCompanySettings({
              pos_config: { receipt: { width_mm: Number(paperWidthMm) } },
            })
          : Promise.resolve(),
      ])
      setSaved(true)
      setTimeout(() => refreshPreview(), 300)
    } catch {
      showError(t('settings:receipt.errorSave'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-lg font-semibold">{t('settings:receipt.title')}</h2>
        <p className="text-sm text-slate-500 mt-1">{t('settings:receipt.subtitle')}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">{t('settings:receipt.paperWidth')}</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                className="w-28 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={paperWidthMm}
                min={48}
                max={120}
                onChange={(e) => setPaperWidthMm(e.target.value === '' ? '' : Number(e.target.value))}
              />
              <span className="text-xs text-slate-500">{t('settings:receipt.paperWidthHint')}</span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">{t('settings:receipt.footerMessage')}</label>
            <input
              type="text"
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={config.footer_message}
              maxLength={80}
              onChange={(e) => handleChange('footer_message', e.target.value)}
              placeholder={t('settings:receipt.defaultFooter')}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">{t('settings:receipt.customHeader')}</label>
            <input
              type="text"
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={config.custom_header}
              maxLength={80}
              onChange={(e) => handleChange('custom_header', e.target.value)}
              placeholder={t('settings:receipt.customHeaderPlaceholder')}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">{t('settings:receipt.customFooter')}</label>
            <textarea
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={2}
              value={config.custom_footer}
              maxLength={160}
              onChange={(e) => handleChange('custom_footer', e.target.value)}
              placeholder={t('settings:receipt.customFooterPlaceholder')}
            />
          </div>

          <fieldset className="space-y-2">
            <legend className="text-sm font-medium mb-2">{t('settings:receipt.infoToShow')}</legend>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={config.show_tax_breakdown}
                onChange={(e) => handleChange('show_tax_breakdown', e.target.checked)}
                className="accent-blue-600"
              />
              {t('settings:receipt.showTaxBreakdown')}
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={config.show_cashier}
                onChange={(e) => handleChange('show_cashier', e.target.checked)}
                className="accent-blue-600"
              />
              {t('settings:receipt.showCashier')}
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={config.show_customer}
                onChange={(e) => handleChange('show_customer', e.target.checked)}
                className="accent-blue-600"
              />
              {t('settings:receipt.showCustomer')}
            </label>
          </fieldset>

          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? t('settings:receipt.saving') : t('settings:receipt.save')}
            </button>
            {saved && <span className="text-sm text-green-600">{t('settings:receipt.saved')}</span>}
            <button
              onClick={refreshPreview}
              disabled={loadingPreview}
              className="px-3 py-2 border rounded text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50"
            >
              {t('settings:receipt.refreshPreview')}
            </button>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">{t('settings:receipt.preview')}</span>
            {loadingPreview && <span className="text-xs text-slate-400">{t('settings:receipt.previewUpdating')}</span>}
          </div>
          <div
            className="bg-white border-2 border-dashed border-slate-300 rounded p-3 overflow-x-auto"
            style={{ maxWidth: 320 }}
          >
            <pre
              className="text-xs leading-snug font-mono whitespace-pre text-slate-800"
              style={{ fontSize: 10, lineHeight: '1.4' }}
            >
              {loadingPreview
                ? t('settings:receipt.previewLoading')
                : preview || t('settings:receipt.previewEmpty')}
            </pre>
          </div>
          <p className="text-xs text-slate-400 mt-2">{t('settings:receipt.previewHint')}</p>
        </div>
      </div>
    </div>
  )
}
