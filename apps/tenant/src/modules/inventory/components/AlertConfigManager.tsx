/** AlertConfigManager — Gestión de configuraciones de alertas de inventario */
import React, { useState, useEffect } from 'react'
import {
  listAlertConfigs,
  createAlertConfig,
  updateAlertConfig,
  deleteAlertConfig,
  testAlertConfig,
  checkAlerts,
  type AlertConfig,
} from '../services'
import { useToast, getErrorMessage } from '../../../shared/toast'

// ─── Tipos ─────────────────────────────────────────────────────────────────────

interface AlertConfigForm
  extends Omit<AlertConfig, 'id' | 'created_at' | 'updated_at' | 'last_checked_at' | 'next_check_at'> {}

const DEFAULT_FORM: AlertConfigForm = {
  name: '',
  is_active: true,
  alert_type: 'low_stock',
  threshold_type: 'fixed',
  threshold_value: 10,
  warehouse_ids: [],
  category_ids: [],
  product_ids: [],
  notify_email: false,
  email_recipients: [],
  notify_whatsapp: false,
  whatsapp_numbers: [],
  notify_telegram: false,
  telegram_chat_ids: [],
  check_frequency_minutes: 60,
  cooldown_hours: 24,
  max_alerts_per_day: 10,
}

const ALERT_TYPE_LABELS: Record<string, string> = {
  low_stock: 'Stock bajo',
  out_of_stock: 'Sin stock',
  expiring_stock: 'Por caducar',
  high_waste: 'Merma alta',
}

const ALERT_TYPE_COLORS: Record<string, string> = {
  low_stock: 'bg-orange-100 text-orange-700',
  out_of_stock: 'bg-red-100 text-red-700',
  expiring_stock: 'bg-yellow-100 text-yellow-700',
  high_waste: 'bg-purple-100 text-purple-700',
}

// ─── Componente ────────────────────────────────────────────────────────────────

export default function AlertConfigManager() {
  const { success, error: toastError, info } = useToast()
  const [configs, setConfigs] = useState<AlertConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingConfig, setEditingConfig] = useState<AlertConfig | null>(null)
  const [formData, setFormData] = useState<AlertConfigForm>(DEFAULT_FORM)
  const [saving, setSaving] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState<AlertConfig | null>(null)
  const [testing, setTesting] = useState<string | null>(null)
  const [checking, setChecking] = useState(false)

  useEffect(() => { loadConfigs() }, [])

  const loadConfigs = async () => {
    try {
      setLoading(true)
      setConfigs(await listAlertConfigs())
    } catch (e) {
      toastError(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (editingConfig) {
        await updateAlertConfig(editingConfig.id, formData)
        success('Configuración actualizada')
      } else {
        await createAlertConfig(formData)
        success('Configuración creada')
      }
      setShowForm(false)
      setEditingConfig(null)
      setFormData(DEFAULT_FORM)
      loadConfigs()
    } catch (e) {
      toastError(getErrorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  const handleEdit = (config: AlertConfig) => {
    setEditingConfig(config)
    setFormData({
      name: config.name,
      is_active: config.is_active,
      alert_type: config.alert_type,
      threshold_type: config.threshold_type,
      threshold_value: config.threshold_value,
      warehouse_ids: [...config.warehouse_ids],
      category_ids: [...config.category_ids],
      product_ids: [...config.product_ids],
      notify_email: config.notify_email,
      email_recipients: [...config.email_recipients],
      notify_whatsapp: config.notify_whatsapp,
      whatsapp_numbers: [...config.whatsapp_numbers],
      notify_telegram: config.notify_telegram,
      telegram_chat_ids: [...config.telegram_chat_ids],
      check_frequency_minutes: config.check_frequency_minutes,
      cooldown_hours: config.cooldown_hours,
      max_alerts_per_day: config.max_alerts_per_day,
    })
    setShowForm(true)
  }

  const handleToggleActive = async (config: AlertConfig) => {
    try {
      await updateAlertConfig(config.id, { is_active: !config.is_active })
      setConfigs((prev) =>
        prev.map((c) => (c.id === config.id ? { ...c, is_active: !c.is_active } : c)),
      )
    } catch (e) {
      toastError(getErrorMessage(e))
    }
  }

  const handleDeleteConfirmed = async () => {
    if (!confirmDelete) return
    try {
      await deleteAlertConfig(confirmDelete.id)
      success('Configuración eliminada')
      setConfirmDelete(null)
      loadConfigs()
    } catch (e) {
      toastError(getErrorMessage(e))
      setConfirmDelete(null)
    }
  }

  const handleTest = async (configId: string) => {
    setTesting(configId)
    try {
      const result = await testAlertConfig(configId)
      if (result.channels_sent.length > 0) {
        success(`Prueba enviada por: ${result.channels_sent.join(', ')}`)
      } else {
        info('Prueba ejecutada — sin canales activos')
      }
    } catch (e) {
      toastError(getErrorMessage(e))
    } finally {
      setTesting(null)
    }
  }

  const handleCheckAlerts = async () => {
    setChecking(true)
    try {
      const result = await checkAlerts()
      info(`${result.alerts_sent} alerta${result.alerts_sent !== 1 ? 's' : ''} enviada${result.alerts_sent !== 1 ? 's' : ''}`)
    } catch (e) {
      toastError(getErrorMessage(e))
    } finally {
      setChecking(false)
    }
  }

  const set = (field: keyof AlertConfigForm, value: unknown) =>
    setFormData((prev) => ({ ...prev, [field]: value }))

  const closeForm = () => {
    setShowForm(false)
    setEditingConfig(null)
    setFormData(DEFAULT_FORM)
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="p-8 text-center text-gray-400 text-sm">Cargando configuraciones…</div>
    )
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Alertas de inventario</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Configura cuándo y cómo recibir notificaciones de stock
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleCheckAlerts}
            disabled={checking}
            className="px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            {checking ? 'Verificando…' : 'Verificar ahora'}
          </button>
          <button
            onClick={() => { setEditingConfig(null); setFormData(DEFAULT_FORM); setShowForm(true) }}
            className="px-4 py-2 text-sm font-semibold bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            + Nueva alerta
          </button>
        </div>
      </div>

      {/* Lista */}
      {configs.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <div className="text-4xl mb-3">🔔</div>
          <p className="font-medium text-gray-500">Sin configuraciones de alerta</p>
          <p className="text-sm mt-1">Crea una para recibir avisos cuando el stock baje.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {configs.map((config) => (
            <div
              key={config.id}
              className={`bg-white border rounded-xl p-4 transition-opacity ${config.is_active ? '' : 'opacity-60'}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 min-w-0">
                  {/* Toggle activo */}
                  <button
                    type="button"
                    onClick={() => handleToggleActive(config)}
                    title={config.is_active ? 'Desactivar' : 'Activar'}
                    className={`mt-0.5 relative shrink-0 inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${
                      config.is_active ? 'bg-blue-600' : 'bg-gray-300'
                    }`}
                  >
                    <span
                      className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform ${
                        config.is_active ? 'translate-x-4' : 'translate-x-0.5'
                      }`}
                    />
                  </button>

                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-gray-900">{config.name}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${ALERT_TYPE_COLORS[config.alert_type] ?? 'bg-gray-100 text-gray-600'}`}>
                        {ALERT_TYPE_LABELS[config.alert_type] ?? config.alert_type}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500 mt-0.5">
                      Umbral: <strong>{config.threshold_value}{config.threshold_type === 'percentage' ? '%' : ' uds.'}</strong>
                      {' · '}cada <strong>{config.check_frequency_minutes} min</strong>
                    </p>
                    <div className="flex gap-1.5 mt-2 flex-wrap">
                      {config.notify_email && (
                        <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full border border-blue-100">
                          ✉ Email
                        </span>
                      )}
                      {config.notify_whatsapp && (
                        <span className="text-xs bg-green-50 text-green-700 px-2 py-0.5 rounded-full border border-green-100">
                          WhatsApp
                        </span>
                      )}
                      {config.notify_telegram && (
                        <span className="text-xs bg-sky-50 text-sky-700 px-2 py-0.5 rounded-full border border-sky-100">
                          Telegram
                        </span>
                      )}
                      {!config.notify_email && !config.notify_whatsapp && !config.notify_telegram && (
                        <span className="text-xs text-gray-400 italic">sin canales</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 shrink-0">
                  <button
                    onClick={() => handleTest(config.id)}
                    disabled={testing === config.id}
                    className="px-2.5 py-1 text-xs font-medium text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                  >
                    {testing === config.id ? '…' : 'Probar'}
                  </button>
                  <button
                    onClick={() => handleEdit(config)}
                    className="px-2.5 py-1 text-xs font-medium text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50"
                  >
                    Editar
                  </button>
                  <button
                    onClick={() => setConfirmDelete(config)}
                    className="px-2.5 py-1 text-xs font-medium text-red-500 border border-red-200 rounded-lg hover:bg-red-50"
                  >
                    Eliminar
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Modal formulario ──────────────────────────────────────────────────── */}
      {showForm && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={closeForm}
        >
          <div
            className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between rounded-t-2xl">
              <h3 className="text-lg font-semibold text-gray-900">
                {editingConfig ? 'Editar alerta' : 'Nueva alerta'}
              </h3>
              <button onClick={closeForm} className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-5">

              {/* Nombre + Activo */}
              <div className="flex items-end gap-3">
                <label className="flex-1 text-xs text-gray-500 font-medium">
                  Nombre de la alerta *
                  <input
                    type="text" required value={formData.name}
                    onChange={(e) => set('name', e.target.value)}
                    placeholder="Ej: Stock bajo de harinas"
                    className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
                  />
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-600 pb-2 cursor-pointer">
                  <input
                    type="checkbox" checked={formData.is_active}
                    onChange={(e) => set('is_active', e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300 text-blue-600"
                  />
                  Activa
                </label>
              </div>

              {/* Tipo + Umbral */}
              <div className="grid grid-cols-2 gap-4">
                <label className="text-xs text-gray-500 font-medium">
                  Tipo de alerta
                  <select
                    value={formData.alert_type}
                    onChange={(e) => set('alert_type', e.target.value)}
                    className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="low_stock">Stock bajo</option>
                    <option value="out_of_stock">Sin stock</option>
                    <option value="expiring_stock">Por caducar</option>
                    <option value="high_waste">Merma alta</option>
                  </select>
                </label>
                <label className="text-xs text-gray-500 font-medium">
                  Umbral ({formData.threshold_type === 'percentage' ? '%' : 'unidades'})
                  <div className="flex gap-1.5 mt-1">
                    <input
                      type="number" step="0.01" required value={formData.threshold_value}
                      onChange={(e) => set('threshold_value', parseFloat(e.target.value))}
                      className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
                    />
                    <select
                      value={formData.threshold_type}
                      onChange={(e) => set('threshold_type', e.target.value)}
                      className="border border-gray-300 rounded-lg px-2 py-2 text-sm focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="fixed">uds.</option>
                      <option value="percentage">%</option>
                    </select>
                  </div>
                </label>
              </div>

              {/* Frecuencia */}
              <div className="grid grid-cols-3 gap-3">
                <label className="text-xs text-gray-500 font-medium">
                  Frecuencia (min)
                  <input
                    type="number" min={5} value={formData.check_frequency_minutes}
                    onChange={(e) => set('check_frequency_minutes', parseInt(e.target.value))}
                    className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
                  />
                </label>
                <label className="text-xs text-gray-500 font-medium">
                  Cooldown (h)
                  <input
                    type="number" min={0} value={formData.cooldown_hours}
                    onChange={(e) => set('cooldown_hours', parseInt(e.target.value))}
                    className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
                  />
                </label>
                <label className="text-xs text-gray-500 font-medium">
                  Máx. por día
                  <input
                    type="number" min={1} value={formData.max_alerts_per_day}
                    onChange={(e) => set('max_alerts_per_day', parseInt(e.target.value))}
                    className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
                  />
                </label>
              </div>

              {/* Canales */}
              <div className="space-y-3 border-t border-gray-100 pt-4">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Canales de notificación</p>

                {/* Email */}
                <div className="space-y-1.5">
                  <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                    <input
                      type="checkbox" checked={formData.notify_email}
                      onChange={(e) => set('notify_email', e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-blue-600"
                    />
                    ✉ Email
                  </label>
                  {formData.notify_email && (
                    <textarea
                      rows={2}
                      placeholder="emails separados por coma"
                      value={formData.email_recipients.join(', ')}
                      onChange={(e) => set('email_recipients', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
                    />
                  )}
                </div>

                {/* WhatsApp */}
                <div className="space-y-1.5">
                  <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                    <input
                      type="checkbox" checked={formData.notify_whatsapp}
                      onChange={(e) => set('notify_whatsapp', e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-blue-600"
                    />
                    WhatsApp
                  </label>
                  {formData.notify_whatsapp && (
                    <textarea
                      rows={2}
                      placeholder="números separados por coma (ej: +34123456789)"
                      value={formData.whatsapp_numbers.join(', ')}
                      onChange={(e) => set('whatsapp_numbers', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
                    />
                  )}
                </div>

                {/* Telegram */}
                <div className="space-y-1.5">
                  <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                    <input
                      type="checkbox" checked={formData.notify_telegram}
                      onChange={(e) => set('notify_telegram', e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-blue-600"
                    />
                    Telegram
                  </label>
                  {formData.notify_telegram && (
                    <textarea
                      rows={2}
                      placeholder="chat IDs separados por coma"
                      value={formData.telegram_chat_ids.join(', ')}
                      onChange={(e) => set('telegram_chat_ids', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
                    />
                  )}
                </div>
              </div>

              {/* Acciones */}
              <div className="flex gap-3 pt-2">
                <button
                  type="submit" disabled={saving}
                  className="flex-1 bg-blue-600 text-white py-2 rounded-lg font-semibold text-sm hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? 'Guardando…' : editingConfig ? 'Guardar cambios' : 'Crear alerta'}
                </button>
                <button
                  type="button" onClick={closeForm}
                  className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-lg font-medium text-sm hover:bg-gray-50"
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Modal confirmación eliminar ───────────────────────────────────────── */}
      {confirmDelete && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={() => setConfirmDelete(null)}
        >
          <div
            className="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Eliminar alerta</h3>
            <p className="text-sm text-gray-600 mb-6">
              ¿Eliminar <strong>"{confirmDelete.name}"</strong>? Esta acción no se puede deshacer.
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleDeleteConfirmed}
                className="flex-1 bg-red-600 text-white py-2 rounded-lg font-semibold text-sm hover:bg-red-700"
              >
                Eliminar
              </button>
              <button
                onClick={() => setConfirmDelete(null)}
                className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-lg font-medium text-sm hover:bg-gray-50"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
