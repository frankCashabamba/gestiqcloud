import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useToast, getErrorMessage } from '../../../shared/toast'

interface ModuleConfig {
  [key: string]: any
}

interface ModuleConfigFormProps {
  moduleId: string
  moduleName: string
  config: ModuleConfig
  onSave: (moduleId: string, config: ModuleConfig) => Promise<void>
  onClose: () => void
}

// Configuraciones específicas por módulo — todos usan labelKey para i18n
const MODULE_SCHEMAS: Record<string, any[]> = {
  pos: [
    { key: 'ticket_width_mm', labelKey: 'settings:moduleConfig.ticketWidth', type: 'select', options: [58, 80], default: 58 },
    { key: 'price_includes_tax', labelKey: 'settings:moduleConfig.priceIncludesTax', type: 'boolean', default: true },
    { key: 'return_window_days', labelKey: 'settings:moduleConfig.returnWindowDays', type: 'number', default: 15 },
    { key: 'allow_negative_stock', labelKey: 'settings:moduleConfig.allowNegativeStock', type: 'boolean', default: false },
    { key: 'auto_print', labelKey: 'settings:moduleConfig.autoPrint', type: 'boolean', default: false },
  ],
  inventory: [
    { key: 'track_lots', labelKey: 'settings:moduleConfig.trackLots', type: 'boolean', default: false },
    { key: 'track_expiry', labelKey: 'settings:moduleConfig.trackExpiry', type: 'boolean', default: false },
    { key: 'allow_negative', labelKey: 'settings:moduleConfig.allowNegative', type: 'boolean', default: false },
    { key: 'multi_warehouse', labelKey: 'settings:moduleConfig.multiWarehouse', type: 'boolean', default: false },
    { key: 'min_stock_alert', labelKey: 'settings:moduleConfig.minStockAlert', type: 'number', default: 10 },
  ],
  invoicing: [
    { key: 'default_series', labelKey: 'settings:moduleConfig.defaultSeries', type: 'text', default: 'F' },
    { key: 'auto_number', labelKey: 'settings:moduleConfig.autoNumber', type: 'boolean', default: true },
    { key: 'include_logo', labelKey: 'settings:moduleConfig.includeLogo', type: 'boolean', default: true },
    { key: 'payment_terms_days', labelKey: 'settings:moduleConfig.paymentTermsDays', type: 'number', default: 30 },
  ],
  einvoicing: [
    { key: 'auto_send', labelKey: 'settings:moduleConfig.autoSend', type: 'boolean', default: false },
    { key: 'cert_uploaded', labelKey: 'settings:moduleConfig.certUploaded', type: 'boolean', default: false, readonly: true },
    { key: 'test_mode', labelKey: 'settings:moduleConfig.testMode', type: 'boolean', default: true },
  ],
  crm: [
    { key: 'auto_assign', labelKey: 'settings:moduleConfig.autoAssignCustomers', type: 'boolean', default: false },
    { key: 'lead_score', labelKey: 'settings:moduleConfig.leadScore', type: 'boolean', default: true },
    { key: 'email_notifications', labelKey: 'settings:moduleConfig.emailNotifications', type: 'boolean', default: true },
  ],
  purchases: [
    { key: 'approval_required', labelKey: 'settings:moduleConfig.approvalRequired', type: 'boolean', default: true },
    { key: 'min_approval_amount', labelKey: 'settings:moduleConfig.minApprovalAmount', type: 'number', default: 1000 },
    { key: 'auto_create_po', labelKey: 'settings:moduleConfig.autoCreateOrder', type: 'boolean', default: false },
  ],
  expenses: [
    { key: 'require_receipt', labelKey: 'settings:moduleConfig.requireReceipt', type: 'boolean', default: true },
    { key: 'approval_workflow', labelKey: 'settings:moduleConfig.approvalWorkflow', type: 'boolean', default: true },
    { key: 'categories_required', labelKey: 'settings:moduleConfig.categoriesRequired', type: 'boolean', default: true },
  ],
}

export default function ModuleConfigForm({ moduleId, moduleName, config, onSave, onClose }: ModuleConfigFormProps) {
  const { t } = useTranslation(['settings', 'common'])
  const [formData, setFormData] = useState<ModuleConfig>(config || {})
  const [saving, setSaving] = useState(false)
  const { success, error } = useToast()
  const schema = MODULE_SCHEMAS[moduleId] || []

  useEffect(() => {
    const defaults: ModuleConfig = {}
    schema.forEach(field => {
      if (formData[field.key] === undefined && field.default !== undefined) {
        defaults[field.key] = field.default
      }
    })
    if (Object.keys(defaults).length > 0) {
      setFormData(prev => ({ ...prev, ...defaults }))
    }
  }, [moduleId])

  const handleSave = async () => {
    try {
      setSaving(true)
      await onSave(moduleId, formData)
      success(t('settings:moduleConfig.saved', { moduleName }))
      onClose()
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  const renderField = (field: any) => {
    const value = formData[field.key]
    const fieldLabel = field.labelKey ? t(field.labelKey) : field.label

    switch (field.type) {
      case 'boolean':
        return (
          <div key={field.key} className="flex items-center justify-between p-3 rounded-lg" style={{ background: 'color-mix(in srgb, var(--gc-muted) 40%, transparent)' }}>
            <label className="gc-label mb-0">{fieldLabel}</label>
            <button
              type="button"
              disabled={field.readonly}
              onClick={() => setFormData(prev => ({ ...prev, [field.key]: !value }))}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${field.readonly ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'} ${value ? 'bg-green-500' : 'bg-gray-300'}`}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${value ? 'translate-x-6' : 'translate-x-1'}`} />
            </button>
          </div>
        )

      case 'number':
        return (
          <div key={field.key}>
            <label className="gc-label">{fieldLabel}</label>
            <input
              type="number"
              value={value ?? field.default ?? ''}
              onChange={(e) => setFormData(prev => ({ ...prev, [field.key]: parseInt(e.target.value) || 0 }))}
              className="gc-input"
            />
          </div>
        )

      case 'select':
        return (
          <div key={field.key}>
            <label className="gc-label">{fieldLabel}</label>
            <select
              value={value ?? field.default ?? ''}
              onChange={(e) => setFormData(prev => ({ ...prev, [field.key]: e.target.value }))}
              className="gc-input"
            >
              {field.options.map((opt: any) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          </div>
        )

      case 'text':
      default:
        return (
          <div key={field.key}>
            <label className="gc-label">{fieldLabel}</label>
            <input
              type="text"
              value={value ?? field.default ?? ''}
              onChange={(e) => setFormData(prev => ({ ...prev, [field.key]: e.target.value }))}
              className="gc-input"
            />
          </div>
        )
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(4px)' }}>
      <div className="gc-card w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col p-0">
        {/* Header */}
        <div className="px-6 py-5" style={{ borderBottom: '1px solid var(--gc-border)' }}>
          <h2 className="gc-page-header__title">{t('settings:moduleConfig.title', { moduleName })}</h2>
          <p className="gc-page-header__subtitle mt-1">{t('settings:moduleConfig.subtitle')}</p>
        </div>

        {/* Body */}
        <div className="px-6 py-5 overflow-y-auto flex-1">
          {schema.length === 0 ? (
            <p className="text-sm text-center py-8" style={{ color: 'var(--gc-muted-foreground)' }}>
              {t('settings:moduleConfig.noConfig')}
            </p>
          ) : (
            <div className="space-y-3">
              {schema.map(field => renderField(field))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 flex justify-end gap-3" style={{ borderTop: '1px solid var(--gc-border)' }}>
          <button type="button" onClick={onClose} disabled={saving} className="gc-btn gc-btn--ghost">
            {t('common:cancel')}
          </button>
          <button type="button" onClick={handleSave} disabled={saving} className="gc-btn gc-btn--primary">
            {saving ? t('common:saving') : t('common:save')}
          </button>
        </div>
      </div>
    </div>
  )
}
