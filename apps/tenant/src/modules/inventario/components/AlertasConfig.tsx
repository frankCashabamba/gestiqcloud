// apps/tenant/src/modules/inventario/components/AlertasConfig.tsx (UTF-8)
import React, { useState, useEffect } from 'react'
import {
  listStockAlerts,
  updateReorderPoint,
  resolveAlert,
  configureNotificationChannel,
  testNotification,
  fetchProductos,
} from '../services/inventario'
import type { StockAlert, NotificationChannel, NotificationChannelConfig } from '../types/alertas'
import type { Producto } from '../types/producto'
import { ensureArray } from '../../../shared/utils/array'

// Componente principal
export function AlertasConfig() {
  const [activeTab, setActiveTab] = useState<'config' | 'alerts' | 'channels'>('alerts')

  return (
    <div className="p-4 max-w-7xl mx-auto">
      <h2 className="font-semibold text-2xl mb-6">Configuración de Alertas de Stock</h2>

      {/* Tabs */}
      <div className="border-b mb-6">
        <div className="flex gap-4">
          <button
            onClick={() => setActiveTab('alerts')}
            className={`pb-2 px-3 font-medium transition-colors ${
              activeTab === 'alerts' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Alertas Activas
          </button>
          <button
            onClick={() => setActiveTab('config')}
            className={`pb-2 px-3 font-medium transition-colors ${
              activeTab === 'config' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Configurar Producto
          </button>
          <button
            onClick={() => setActiveTab('channels')}
            className={`pb-2 px-3 font-medium transition-colors ${
              activeTab === 'channels' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Canales de Notificación
          </button>
        </div>
      </div>

      {/* Content */}
      {activeTab === 'alerts' && <AlertasTable />}
      {activeTab === 'config' && <ConfigurarProducto />}
      {activeTab === 'channels' && <CanalesNotificacion />}
    </div>
  )
}

// Sección: Configurar producto
function ConfigurarProducto() {
  const [productos, setProductos] = useState<Producto[]>([])
  const [selectedProductId, setSelectedProductId] = useState<string>('')
  const [stockMinimo, setStockMinimo] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    fetchProductos().then((data) => setProductos(ensureArray(data)))
  }, [])

  const handleSave = async () => {
    setError(null)
    setSuccess(null)

    if (!selectedProductId) {
      setError('Selecciona un producto')
      return
    }
    if (!stockMinimo || parseFloat(stockMinimo) < 0) {
      setError('Ingresa un stock mínimo válido')
      return
    }

    setLoading(true)
    try {
      await updateReorderPoint(selectedProductId, parseFloat(stockMinimo))
      setSuccess('Configuración guardada correctamente')
      setSelectedProductId('')
      setStockMinimo('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al guardar')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-lg border p-6 max-w-2xl">
      <h3 className="font-semibold text-lg mb-4">Configurar Alertas por Producto</h3>

      {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">{error}</div>}
      {success && <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded text-sm">{success}</div>}

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Producto</label>
          <select
            value={selectedProductId}
            onChange={(e) => setSelectedProductId(e.target.value)}
            className="w-full px-3 py-2 border rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">Selecciona…</option>
            {productos.map((p) => (
              <option key={p.id} value={String(p.id)}>
                {p.sku ? `${p.sku} — ` : ''}
                {p.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Stock Mínimo</label>
          <input
            value={stockMinimo}
            onChange={(e) => setStockMinimo(e.target.value)}
            type="number"
            min={0}
            step={1}
            className="w-full px-3 py-2 border rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div className="flex gap-2">
          <button onClick={handleSave} disabled={loading} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-60">
            Guardar
          </button>
          <button onClick={() => { setSelectedProductId(''); setStockMinimo(''); }} className="px-4 py-2 bg-gray-100 text-gray-800 rounded hover:bg-gray-200">
            Limpiar
          </button>
        </div>
      </div>
    </div>
  )
}

// Sección: Tabla de alertas activas
function AlertasTable() {
  const [alerts, setAlerts] = useState<StockAlert[]>([])
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState<'all' | 'pending' | 'resolved' | 'ignored'>('all')

  const loadAlerts = async () => {
    setLoading(true)
    try {
      const data = await listStockAlerts()
      setAlerts(ensureArray(data))
    } catch (err) {
      console.error('Error loading alerts:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAlerts()
  }, [])

  const handleResolve = async (alertId: string) => {
    try {
      await resolveAlert(alertId)
      await loadAlerts()
    } catch (err) {
      console.error('Error resolving alert:', err)
    }
  }

  const filtered = alerts.filter((a) => filter === 'all' || a.estado === filter)

  return (
    <div className="bg-white rounded-lg border">
      <div className="p-4 border-b flex items-center justify-between">
        <h3 className="font-semibold text-lg">Alertas Activas</h3>

        <div className="flex gap-2">
          {(['all', 'pending', 'resolved', 'ignored'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 text-sm rounded transition-colors ${
                filter === f ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {f === 'all' ? 'Todas' : f === 'pending' ? 'Pendientes' : f === 'resolved' ? 'Resueltas' : 'Ignoradas'}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="p-8 text-center text-gray-500">Cargando alertas...</div>
      ) : filtered.length === 0 ? (
        <div className="p-8 text-center text-gray-500">No hay alertas {filter !== 'all' && `en estado "${filter}"`}</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Producto</th>
                <th className="px-4 py-3 text-left font-medium">SKU</th>
                <th className="px-4 py-3 text-right font-medium">Stock Actual</th>
                <th className="px-4 py-3 text-right font-medium">Stock Mínimo</th>
                <th className="px-4 py-3 text-left font-medium">Estado</th>
                <th className="px-4 py-3 text-left font-medium">Última Notif.</th>
                <th className="px-4 py-3 text-right font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.map((alert) => (
                <tr key={alert.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{alert.producto_nombre}</td>
                  <td className="px-4 py-3 text-gray-600">{alert.producto_sku}</td>
                  <td className="px-4 py-3 text-right">
                    <span
                      className={`font-medium ${alert.stock_actual <= alert.stock_minimo * 0.5 ? 'text-red-600' : 'text-orange-600'}`}
                    >
                      {alert.stock_actual}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-600">{alert.stock_minimo}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex px-2 py-1 text-xs font-medium rounded ${
                        alert.estado === 'pending'
                          ? 'bg-orange-100 text-orange-700'
                          : alert.estado === 'resolved'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      {alert.estado === 'pending' ? 'Pendiente' : alert.estado === 'resolved' ? 'Resuelta' : 'Ignorada'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {alert.ultima_notificacion
                      ? new Date(alert.ultima_notificacion).toLocaleString('es-ES', {
                          day: '2-digit',
                          month: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit',
                        })
                      : '-'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {alert.estado === 'pending' && (
                      <button onClick={() => handleResolve(alert.id)} className="text-blue-600 hover:text-blue-800 text-sm font-medium">
                        Resolver
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// Sección: Canales de notificación
function CanalesNotificacion() {
  const [tipo, setTipo] = useState<NotificationChannel>('email')
  const [enabled, setEnabled] = useState(true)
  const [details, setDetails] = useState<any>({ email: '', phone: '', chat_id: '' })
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  const saveChannel = async () => {
    setSaving(true)
    setMsg(null)
    try {
      const cfg: NotificationChannelConfig = { tipo, enabled, config: details }
      await configureNotificationChannel(tipo, cfg as any)
      setMsg('Configuración guardada correctamente')
    } catch (e) {
      setMsg('Error al guardar la configuración')
    } finally {
      setSaving(false)
    }
  }

  const sendTest = async () => {
    setMsg(null)
    try {
      await testNotification(tipo, details)
      setMsg('Notificación de prueba enviada correctamente')
    } catch (e) {
      setMsg('Error al enviar prueba')
    }
  }

  return (
    <div className="bg-white rounded-lg border p-6 max-w-2xl">
      <h3 className="font-semibold text-lg mb-4">Canales de Notificación</h3>
      {msg && <div className="mb-4 p-3 bg-gray-50 border text-sm">{msg}</div>}

      <div className="grid grid-cols-1 gap-4">
        <div>
          <label className="block text-sm font-medium mb-2">Canal</label>
          <select value={tipo} onChange={(e) => setTipo(e.target.value as any)} className="w-full px-3 py-2 border rounded">
            <option value="email">Email</option>
            <option value="whatsapp">WhatsApp</option>
            <option value="telegram">Telegram</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Habilitado</label>
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
        </div>

        {tipo === 'email' && (
          <div>
            <label className="block text-sm font-medium mb-2">Email</label>
            <input value={details.email || ''} onChange={(e) => setDetails({ ...details, email: e.target.value })} className="w-full px-3 py-2 border rounded" />
          </div>
        )}
        {tipo === 'whatsapp' && (
          <div>
            <label className="block text-sm font-medium mb-2">Teléfono</label>
            <input value={details.phone || ''} onChange={(e) => setDetails({ ...details, phone: e.target.value })} className="w-full px-3 py-2 border rounded" />
          </div>
        )}
        {tipo === 'telegram' && (
          <div>
            <label className="block text-sm font-medium mb-2">Chat ID</label>
            <input value={details.chat_id || ''} onChange={(e) => setDetails({ ...details, chat_id: e.target.value })} className="w-full px-3 py-2 border rounded" />
          </div>
        )}

        <div className="flex gap-2">
          <button onClick={saveChannel} disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-60">
            Guardar canal
          </button>
          <button onClick={sendTest} className="px-4 py-2 bg-gray-100 text-gray-800 rounded hover:bg-gray-200">
            Enviar prueba
          </button>
        </div>
      </div>
    </div>
  )
}
