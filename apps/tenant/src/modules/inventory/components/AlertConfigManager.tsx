/** AlertConfigManager - Gestión de configuraciones de alertas de inventario */
import React, { useState, useEffect } from 'react'
import {
  listAlertConfigs,
  createAlertConfig,
  updateAlertConfig,
  deleteAlertConfig,
  testAlertConfig,
  checkAlerts,
  type AlertConfig
} from '../services'

interface AlertConfigForm extends Omit<AlertConfig, 'id' | 'created_at' | 'updated_at' | 'last_checked_at' | 'next_check_at'> {}

export default function AlertConfigManager() {
  const [configs, setConfigs] = useState<AlertConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingConfig, setEditingConfig] = useState<AlertConfig | null>(null)
  const [formData, setFormData] = useState<AlertConfigForm>({
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
  })

  useEffect(() => {
    loadConfigs()
  }, [])

  const loadConfigs = async () => {
    try {
      setLoading(true)
      const data = await listAlertConfigs()
      setConfigs(data)
    } catch (error) {
      console.error('Error loading alert configs:', error)
      alert('Error loading alert configurations')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (editingConfig) {
        await updateAlertConfig(editingConfig.id, formData)
        alert('Configuration updated successfully')
      } else {
        await createAlertConfig(formData)
        alert('Configuration created successfully')
      }
      setShowForm(false)
      setEditingConfig(null)
      resetForm()
      loadConfigs()
    } catch (error) {
      console.error('Error saving config:', error)
      alert('Error saving configuration')
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

  const handleDelete = async (configId: string) => {
    if (!confirm('Are you sure you want to delete this configuration?')) return
    try {
      await deleteAlertConfig(configId)
      alert('Configuration deleted')
      loadConfigs()
    } catch (error) {
      console.error('Error deleting config:', error)
      alert('Error deleting configuration')
    }
  }

  const handleTest = async (configId: string) => {
    try {
      const result = await testAlertConfig(configId)
      alert(`Test sent. Channels: ${result.channels_sent.join(', ')}`)
    } catch (error) {
      console.error('Error testing config:', error)
      alert('Error sending test')
    }
  }

  const handleCheckAlerts = async () => {
    try {
      const result = await checkAlerts()
      alert(`${result.alerts_sent} alerts sent`)
    } catch (error) {
      console.error('Error checking alerts:', error)
      alert('Error checking alerts')
    }
  }

  const resetForm = () => {
    setFormData({
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
    })
  }

  const updateFormField = (field: keyof AlertConfigForm, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  if (loading) {
    return <div className="p-4 text-center">Loading configurations...</div>
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold">Inventory Alerts</h2>
        <div className="flex gap-2">
          <button
            onClick={handleCheckAlerts}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            Check Alerts
          </button>
          <button
            onClick={() => {
              setEditingConfig(null)
              resetForm()
              setShowForm(true)
            }}
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
          >
            New Configuration
          </button>
        </div>
      </div>

      {/* Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-4xl w-full m-4 max-h-[90vh] overflow-y-auto">
            <h3 className="text-xl font-bold mb-4">
              {editingConfig ? 'Edit Configuration' : 'New Configuration'}
            </h3>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Name</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => updateFormField('name', e.target.value)}
                    className="w-full border rounded px-3 py-2"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Alert Type</label>
                  <select
                    value={formData.alert_type}
                    onChange={(e) => updateFormField('alert_type', e.target.value)}
                    className="w-full border rounded px-3 py-2"
                  >
                    <option value="low_stock">Low Stock</option>
                    <option value="out_of_stock">Out of Stock</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Threshold Type</label>
                  <select
                    value={formData.threshold_type}
                    onChange={(e) => updateFormField('threshold_type', e.target.value)}
                    className="w-full border rounded px-3 py-2"
                  >
                    <option value="fixed">Fixed Quantity</option>
                    <option value="percentage">Percentage</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Threshold Value</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.threshold_value}
                    onChange={(e) => updateFormField('threshold_value', parseFloat(e.target.value))}
                    className="w-full border rounded px-3 py-2"
                    required
                  />
                </div>
              </div>

              {/* Notification Channels */}
              <div className="border-t pt-4">
                <h4 className="font-semibold mb-3">Notification Channels</h4>

                {/* Email */}
                <div className="mb-4">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.notify_email}
                      onChange={(e) => updateFormField('notify_email', e.target.checked)}
                      className="mr-2"
                    />
                    Email
                  </label>
                  {formData.notify_email && (
                    <textarea
                      placeholder="emails separated by comma"
                      value={formData.email_recipients.join(', ')}
                      onChange={(e) => updateFormField('email_recipients', e.target.value.split(',').map(s => s.trim()))}
                      className="w-full border rounded px-3 py-2 mt-2"
                      rows={2}
                    />
                  )}
                </div>

                {/* WhatsApp */}
                <div className="mb-4">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.notify_whatsapp}
                      onChange={(e) => updateFormField('notify_whatsapp', e.target.checked)}
                      className="mr-2"
                    />
                    WhatsApp
                  </label>
                  {formData.notify_whatsapp && (
                    <textarea
                      placeholder="numbers separated by comma (e.g.: +34123456789)"
                      value={formData.whatsapp_numbers.join(', ')}
                      onChange={(e) => updateFormField('whatsapp_numbers', e.target.value.split(',').map(s => s.trim()))}
                      className="w-full border rounded px-3 py-2 mt-2"
                      rows={2}
                    />
                  )}
                </div>

                {/* Telegram */}
                <div className="mb-4">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.notify_telegram}
                      onChange={(e) => updateFormField('notify_telegram', e.target.checked)}
                      className="mr-2"
                    />
                    Telegram
                  </label>
                  {formData.notify_telegram && (
                    <textarea
                      placeholder="chat IDs separated by comma"
                      value={formData.telegram_chat_ids.join(', ')}
                      onChange={(e) => updateFormField('telegram_chat_ids', e.target.value.split(',').map(s => s.trim()))}
                      className="w-full border rounded px-3 py-2 mt-2"
                      rows={2}
                    />
                  )}
                </div>
              </div>

              <div className="flex gap-2 pt-4">
                <button
                  type="submit"
                  className="flex-1 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                >
                  {editingConfig ? 'Update' : 'Create'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowForm(false)
                    setEditingConfig(null)
                  }}
                  className="flex-1 bg-gray-300 px-4 py-2 rounded hover:bg-gray-400"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Config List */}
      <div className="space-y-4">
        {configs.map((config) => (
          <div key={config.id} className="border rounded-lg p-4">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="font-semibold">{config.name}</h3>
                <p className="text-sm text-gray-600">
                  {config.alert_type} • Umbral: {config.threshold_value} •
                  Frequency: {config.check_frequency_minutes}min
                </p>
                <div className="flex gap-2 mt-2">
                  {config.notify_email && <span className="text-xs bg-blue-100 px-2 py-1 rounded">Email</span>}
                  {config.notify_whatsapp && <span className="text-xs bg-green-100 px-2 py-1 rounded">WhatsApp</span>}
                  {config.notify_telegram && <span className="text-xs bg-blue-200 px-2 py-1 rounded">Telegram</span>}
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleTest(config.id)}
                  className="bg-yellow-500 text-white px-3 py-1 rounded text-sm hover:bg-yellow-600"
                >
                  Test
                </button>
                <button
                  onClick={() => handleEdit(config)}
                  className="bg-blue-500 text-white px-3 py-1 rounded text-sm hover:bg-blue-600"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleDelete(config.id)}
                  className="bg-red-500 text-white px-3 py-1 rounded text-sm hover:bg-red-600"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        ))}

        {configs.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            No alert configurations. Create one to get started.
          </div>
        )}
      </div>
    </div>
  )
}
