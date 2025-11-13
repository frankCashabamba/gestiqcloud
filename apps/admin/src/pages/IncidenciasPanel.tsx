/**
 * IncidenciasPanel.tsx
 * Gestión de incidencias con IA auto-resolución
 * Tabs: Activas, Resueltas, Stock Alerts
 */

import React, { useState, useEffect } from 'react'
import { useAuthGuard } from '../hooks/useAuthGuard'
import {
  listIncidents,
  analyzeIncident,
  autoResolveIncident,
  assignIncident,
  closeIncident,
  listStockAlerts,
  notifyStockAlert,
  resolveStockAlert
} from '../services/incidents'
import IncidentDetailModal from '../components/IncidentDetailModal'
import type { Incident, StockAlert } from '../types/incidents'

type Tab = 'activas' | 'resueltas' | 'stock_alerts'

export default function IncidenciasPanel() {
  useAuthGuard('superadmin')

  const [activeTab, setActiveTab] = useState<Tab>('activas')
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [stockAlerts, setStockAlerts] = useState<StockAlert[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null)

  useEffect(() => {
    loadData()
  }, [activeTab])

  const loadData = async () => {
    setLoading(true)
    try {
      if (activeTab === 'stock_alerts') {
        const data = await listStockAlerts({ estado: 'active,notified' })
        setStockAlerts(data)
      } else {
        const estado = activeTab === 'activas' ? 'open,in_progress' : 'resolved,auto_resolved,closed'
        const data = await listIncidents({ estado })
        setIncidents(data)
      }
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAnalyze = async (id: string) => {
    try {
      await analyzeIncident(id)
      await loadData()
      alert('✅ Análisis IA completado')
    } catch (error) {
      console.error('Error analyzing incident:', error)
      alert('❌ Error al analizar incidencia')
    }
  }

  const handleAutoResolve = async (id: string) => {
    try {
      await autoResolveIncident(id)
      await loadData()
      alert('✅ Incidencia auto-resuelta')
    } catch (error) {
      console.error('Error auto-resolving:', error)
      alert('❌ Error al auto-resolver')
    }
  }

  const handleAssign = async (id: string) => {
    const userId = localStorage.getItem('user_id') // O desde AuthContext
    if (!userId) {
      alert('No se pudo obtener el ID de usuario')
      return
    }
    try {
      await assignIncident(id, userId)
      await loadData()
      alert('✅ Incidencia asignada')
    } catch (error) {
      console.error('Error assigning:', error)
      alert('❌ Error al asignar')
    }
  }

  const handleClose = async (id: string) => {
    if (!confirm('¿Cerrar esta incidencia?')) return
    try {
      await closeIncident(id)
      await loadData()
      alert('✅ Incidencia cerrada')
    } catch (error) {
      console.error('Error closing:', error)
      alert('❌ Error al cerrar')
    }
  }

  const handleNotifyStock = async (id: string) => {
    try {
      await notifyStockAlert(id)
      await loadData()
      alert('✅ Notificación enviada')
    } catch (error) {
      console.error('Error notifying:', error)
      alert('❌ Error al notificar')
    }
  }

  const handleResolveStock = async (id: string) => {
    try {
      await resolveStockAlert(id)
      await loadData()
      alert('✅ Alerta resuelta')
    } catch (error) {
      console.error('Error resolving stock alert:', error)
      alert('❌ Error al resolver')
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-200'
      case 'high': return 'bg-orange-100 text-orange-800 border-orange-200'
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'low': return 'bg-blue-100 text-blue-800 border-blue-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const formatDate = (date: string) => {
    return new Date(date).toLocaleString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="admin-shell">
      <header className="mb-6">
        <div className="admin-header">
          <h1 className="admin-title">🚨 Panel de Incidencias</h1>
          <button
            onClick={loadData}
            className="btn btn-primary"
            disabled={loading}
          >
            {loading ? '⏳' : '🔄'} Actualizar
          </button>
        </div>
      </header>

      {/* Tabs */}
      <div className="mb-6 border-b border-gray-200">
        <div className="flex gap-4">
          <button
            onClick={() => setActiveTab('activas')}
            className={`pb-3 px-2 border-b-2 font-medium transition-colors ${
              activeTab === 'activas'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            🔴 Activas ({activeTab === 'activas' ? incidents.length : '-'})
          </button>
          <button
            onClick={() => setActiveTab('resueltas')}
            className={`pb-3 px-2 border-b-2 font-medium transition-colors ${
              activeTab === 'resueltas'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            ✅ Resueltas ({activeTab === 'resueltas' ? incidents.length : '-'})
          </button>
          <button
            onClick={() => setActiveTab('stock_alerts')}
            className={`pb-3 px-2 border-b-2 font-medium transition-colors ${
              activeTab === 'stock_alerts'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            📦 Stock Alerts ({activeTab === 'stock_alerts' ? stockAlerts.length : '-'})
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full"></div>
          <span className="ml-3 text-gray-600">Cargando�</span>
        </div>
      ) : (
        <>
          {/* Tab: Activas / Resueltas */}
          {(activeTab === 'activas' || activeTab === 'resueltas') && (
            <div className="card overflow-hidden">
              {incidents.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  {activeTab === 'activas'
                    ? '🎉 No hay incidencias activas'
                    : 'No hay incidencias resueltas'
                  }
                </div>
              ) : (
                <div className="table-wrap"><table>
                    <thead >
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Severidad
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Título
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Tenant
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Tipo
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Estado
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Creada
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Acciones
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {incidents.map((incident) => (
                        <tr key={incident.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span className={`px-2 py-1 text-xs font-bold rounded border ${getSeverityColor(incident.severidad)}`}>
                              {incident.severidad.toUpperCase()}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="text-sm font-medium text-gray-900">
                              {incident.titulo}
                              {incident.auto_detected && (
                                <span className="ml-2 text-xs bg-purple-100 text-purple-800 px-2 py-0.5 rounded">
                                  🤖 Auto-detect
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600 font-mono">
                            {incident.tenant_id?.substring(0, 8) || 'Sistema'}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                            {incident.tipo}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span className={`px-2 py-1 text-xs font-medium rounded ${
                              incident.auto_resolved
                                ? 'bg-green-100 text-green-800'
                                : incident.estado === 'resolved'
                                ? 'bg-green-100 text-green-800'
                                : incident.estado === 'in_progress'
                                ? 'bg-blue-100 text-blue-800'
                                : 'bg-gray-100 text-gray-800'
                            }`}>
                              {incident.auto_resolved ? '🤖 Auto-resuelto' : incident.estado}
                            </span>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                            {formatDate(incident.created_at)}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm">
                            <div className="flex gap-2">
                              <button
                                onClick={() => setSelectedIncident(incident)}
                                className="text-blue-600 hover:text-blue-800"
                                title="Ver detalle"
                              >
                                🔍
                              </button>
                              {activeTab === 'activas' && (
                                <>
                                  <button
                                    onClick={() => handleAnalyze(incident.id)}
                                    className="text-purple-600 hover:text-purple-800"
                                    title="Analizar con IA"
                                  >
                                    🤖
                                  </button>
                                  <button
                                    onClick={() => handleAutoResolve(incident.id)}
                                    className="text-green-600 hover:text-green-800"
                                    title="Auto-Resolver"
                                  >
                                    ✨
                                  </button>
                                  <button
                                    onClick={() => handleAssign(incident.id)}
                                    className="text-orange-600 hover:text-orange-800"
                                    title="Asignarme"
                                  >
                                    👤
                                  </button>
                                  <button
                                    onClick={() => handleClose(incident.id)}
                                    className="text-gray-600 hover:text-gray-800"
                                    title="Cerrar"
                                  >
                                    ✅
                                  </button>
                                </>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Tab: Stock Alerts */}
          {activeTab === 'stock_alerts' && (
            <div className="card overflow-hidden">
              {stockAlerts.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  📦 No hay alertas de stock activas
                </div>
              ) : (
                <div className="table-wrap"><table>
                    <thead >
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Producto
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Almacén
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Stock Actual
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Mínimo
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Estado
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Detectada
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Acciones
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {stockAlerts.map((alert) => (
                        <tr key={alert.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3">
                            <div className="text-sm font-medium text-gray-900">
                              {alert.product_name}
                            </div>
                            <div className="text-xs text-gray-500 font-mono">
                              {alert.product_id.substring(0, 8)}
                            </div>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                            {alert.warehouse_name}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span className={`text-sm font-bold ${
                              alert.qty_on_hand <= 0 ? 'text-red-600' : 'text-orange-600'
                            }`}>
                              {alert.qty_on_hand}
                            </span>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                            {alert.min_qty}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span className={`px-2 py-1 text-xs font-medium rounded ${
                              alert.estado === 'active' ? 'bg-red-100 text-red-800' :
                              alert.estado === 'notified' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-green-100 text-green-800'
                            }`}>
                              {alert.estado}
                            </span>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                            {formatDate(alert.detected_at)}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm">
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleNotifyStock(alert.id)}
                                className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-xs"
                              >
                                📧 Notificar
                              </button>
                              <button
                                onClick={() => handleResolveStock(alert.id)}
                                className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 text-xs"
                              >
                                ✅ Resolver
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Modal Detalle */}
      {selectedIncident && (
        <IncidentDetailModal
          incident={selectedIncident}
          onClose={() => setSelectedIncident(null)}
          onAnalyze={handleAnalyze}
          onAutoResolve={handleAutoResolve}
          onAssign={handleAssign}
          onCloseIncident={handleClose}
        />
      )}
    </div>
  )
}

