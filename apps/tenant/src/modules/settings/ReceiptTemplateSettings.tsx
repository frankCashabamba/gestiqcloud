import React, { useEffect, useState, useCallback } from 'react'
import api from '../../services/api/client'

interface ReceiptConfig {
  footer_message: string
  show_tax_breakdown: boolean
  show_cashier: boolean
  show_customer: boolean
  custom_header: string
  custom_footer: string
}

const DEFAULT_CONFIG: ReceiptConfig = {
  footer_message: '¡Gracias por su compra!',
  show_tax_breakdown: true,
  show_cashier: true,
  show_customer: true,
  custom_header: '',
  custom_footer: '',
}

export default function ReceiptTemplateSettings() {
  const [config, setConfig] = useState<ReceiptConfig>(DEFAULT_CONFIG)
  const [preview, setPreview] = useState('')
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api.get('/api/v1/tenant/printing/receipt-settings').then((res) => {
      setConfig({ ...DEFAULT_CONFIG, ...res.data })
    }).catch(() => {})
  }, [])

  const refreshPreview = useCallback(() => {
    setLoadingPreview(true)
    api.get('/api/v1/tenant/printing/receipt-preview')
      .then((res) => setPreview(res.data.preview || ''))
      .catch(() => setPreview('Error al generar preview'))
      .finally(() => setLoadingPreview(false))
  }, [])

  useEffect(() => {
    refreshPreview()
  }, [refreshPreview])

  const handleChange = (field: keyof ReceiptConfig, value: string | boolean) => {
    setConfig((prev) => ({ ...prev, [field]: value }))
    setSaved(false)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.post('/api/v1/tenant/printing/receipt-settings', config)
      setSaved(true)
      setTimeout(() => refreshPreview(), 300)
    } catch {
      // keep error silent — user sees no change
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Template de Ticket POS (80mm)</h2>
        <p className="text-sm text-slate-500 mt-1">
          Configura el formato del ticket que se imprime al finalizar una venta.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Formulario de configuración */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Mensaje de pie de página</label>
            <input
              type="text"
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={config.footer_message}
              maxLength={80}
              onChange={(e) => handleChange('footer_message', e.target.value)}
              placeholder="¡Gracias por su compra!"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Encabezado personalizado (opcional)</label>
            <input
              type="text"
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={config.custom_header}
              maxLength={80}
              onChange={(e) => handleChange('custom_header', e.target.value)}
              placeholder="Ej: Promoción: 2x1 en bebidas"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Nota adicional al pie (opcional)</label>
            <textarea
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={2}
              value={config.custom_footer}
              maxLength={160}
              onChange={(e) => handleChange('custom_footer', e.target.value)}
              placeholder="Ej: Válido 30 días para cambios con factura"
            />
          </div>

          <fieldset className="space-y-2">
            <legend className="text-sm font-medium mb-2">Información a mostrar</legend>

            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={config.show_tax_breakdown}
                onChange={(e) => handleChange('show_tax_breakdown', e.target.checked)}
                className="accent-blue-600"
              />
              Mostrar desglose de IVA
            </label>

            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={config.show_cashier}
                onChange={(e) => handleChange('show_cashier', e.target.checked)}
                className="accent-blue-600"
              />
              Mostrar nombre del cajero
            </label>

            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={config.show_customer}
                onChange={(e) => handleChange('show_customer', e.target.checked)}
                className="accent-blue-600"
              />
              Mostrar nombre del cliente (si aplica)
            </label>
          </fieldset>

          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Guardando...' : 'Guardar configuración'}
            </button>
            {saved && (
              <span className="text-sm text-green-600">✓ Guardado</span>
            )}
            <button
              onClick={refreshPreview}
              disabled={loadingPreview}
              className="px-3 py-2 border rounded text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50"
            >
              Actualizar preview
            </button>
          </div>
        </div>

        {/* Preview del ticket */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Vista previa (80mm)</span>
            {loadingPreview && <span className="text-xs text-slate-400">Actualizando...</span>}
          </div>
          <div
            className="bg-white border-2 border-dashed border-slate-300 rounded p-3 overflow-x-auto"
            style={{ maxWidth: 320 }}
          >
            <pre
              className="text-xs leading-snug font-mono whitespace-pre text-slate-800"
              style={{ fontSize: 10, lineHeight: '1.4' }}
            >
              {loadingPreview ? 'Cargando...' : preview || 'Sin preview disponible'}
            </pre>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            El preview usa datos de ejemplo. El ticket real muestra los datos reales de la venta.
          </p>
        </div>
      </div>
    </div>
  )
}
