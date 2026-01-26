import React, { useState, useEffect } from 'react'
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

// Configuraciones específicas por módulo
const MODULE_SCHEMAS: Record<string, any[]> = {
  pos: [
    { key: 'ticket_width_mm', label: 'Ancho de Ticket (mm)', type: 'select', options: [58, 80], default: 58 },
    { key: 'price_includes_tax', label: 'Precio incluye impuestos', type: 'boolean', default: true },
    { key: 'return_window_days', label: 'Días para devoluciones', type: 'number', default: 15 },
    { key: 'allow_negative_stock', label: 'Permitir stock negativo', type: 'boolean', default: false },
    { key: 'auto_print', label: 'Imprimir automáticamente', type: 'boolean', default: false },
  ],
  inventory: [
    { key: 'track_lots', label: 'Gestionar lotes', type: 'boolean', default: false },
    { key: 'track_expiry', label: 'Gestionar caducidad', type: 'boolean', default: false },
    { key: 'allow_negative', label: 'Permitir stock negativo', type: 'boolean', default: false },
    { key: 'multi_warehouse', label: 'Multi-almacén', type: 'boolean', default: false },
    { key: 'min_stock_alert', label: 'Stock mínimo para alertas', type: 'number', default: 10 },
  ],
  invoicing: [
    { key: 'default_series', label: 'Serie por defecto', type: 'text', default: 'F' },
    { key: 'auto_number', label: 'Numeración automática', type: 'boolean', default: true },
    { key: 'include_logo', label: 'Incluir logo en facturas', type: 'boolean', default: true },
    { key: 'payment_terms_days', label: 'Plazo de pago (días)', type: 'number', default: 30 },
  ],
  einvoicing: [
    { key: 'auto_send', label: 'Envío automático a SRI/AEAT', type: 'boolean', default: false },
    { key: 'cert_uploaded', label: 'Certificado digital cargado', type: 'boolean', default: false, readonly: true },
    { key: 'test_mode', label: 'Modo de pruebas', type: 'boolean', default: true },
  ],
  crm: [
    { key: 'auto_assign', label: 'Asignación automática de clientes', type: 'boolean', default: false },
    { key: 'lead_score', label: 'Scoring de leads', type: 'boolean', default: true },
    { key: 'email_notifications', label: 'Notificaciones por email', type: 'boolean', default: true },
  ],
  purchases: [
    { key: 'approval_required', label: 'Requiere aprobación', type: 'boolean', default: true },
    { key: 'min_approval_amount', label: 'Monto mínimo para aprobación', type: 'number', default: 1000 },
    { key: 'auto_create_po', label: 'Crear orden automáticamente', type: 'boolean', default: false },
  ],
  expenses: [
    { key: 'require_receipt', label: 'Comprobante obligatorio', type: 'boolean', default: true },
    { key: 'approval_workflow', label: 'Flujo de aprobación', type: 'boolean', default: true },
    { key: 'categories_required', label: 'Categorías obligatorias', type: 'boolean', default: true },
  ],
}

export default function ModuleConfigForm({ moduleId, moduleName, config, onSave, onClose }: ModuleConfigFormProps) {
  const [formData, setFormData] = useState<ModuleConfig>(config || {})
  const [saving, setSaving] = useState(false)
  const { success, error } = useToast()
  const schema = MODULE_SCHEMAS[moduleId] || []

  useEffect(() => {
    // Inicializar con valores por defecto si no existen
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
      success(`Configuración de ${moduleName} guardada`)
      onClose()
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  const renderField = (field: any) => {
    const value = formData[field.key]

    switch (field.type) {
      case 'boolean':
        return (
          <div key={field.key} className="flex items-center justify-between p-3 bg-gray-50 rounded">
            <label className="font-medium text-gray-700">{field.label}</label>
            <button
              disabled={field.readonly}
              onClick={() => setFormData(prev => ({ ...prev, [field.key]: !value }))}
              className={`
                relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                ${field.readonly ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                ${value ? 'bg-green-600' : 'bg-gray-300'}
              `}
            >
              <span
                className={`
                  inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                  ${value ? 'translate-x-6' : 'translate-x-1'}
                `}
              />
            </button>
          </div>
        )

      case 'number':
        return (
          <div key={field.key} className="space-y-1">
            <label className="block font-medium text-gray-700">{field.label}</label>
            <input
              type="number"
              value={value ?? field.default ?? ''}
              onChange={(e) => setFormData(prev => ({ ...prev, [field.key]: parseInt(e.target.value) || 0 }))}
              className="border border-gray-300 px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        )

      case 'select':
        return (
          <div key={field.key} className="space-y-1">
            <label className="block font-medium text-gray-700">{field.label}</label>
            <select
              value={value ?? field.default ?? ''}
              onChange={(e) => setFormData(prev => ({ ...prev, [field.key]: e.target.value }))}
              className="border border-gray-300 px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
          <div key={field.key} className="space-y-1">
            <label className="block font-medium text-gray-700">{field.label}</label>
            <input
              type="text"
              value={value ?? field.default ?? ''}
              onChange={(e) => setFormData(prev => ({ ...prev, [field.key]: e.target.value }))}
              className="border border-gray-300 px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        )
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-800">
            Configurar {moduleName}
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Personaliza el comportamiento del módulo
          </p>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto flex-1">
          {schema.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <p>No hay configuraciones disponibles para este módulo</p>
            </div>
          ) : (
            <div className="space-y-4">
              {schema.map(field => renderField(field))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  )
}
