/**
 * LogsViewer.tsx
 * Visor de historial de notificaciones del sistema (email/whatsapp/telegram)
 */

import React, { useState, useEffect } from 'react'
import { useAuthGuard } from '../hooks/useAuthGuard'
import { listLogs, exportLogs, getLogStats } from '../services/logs'
import type { LogEntry, LogFilters, LogStats } from '../types/logs'

export default function LogsViewer() {
  useAuthGuard('superadmin')

  const [logs, setLogs] = useState<LogEntry[]>([])
  const [stats, setStats] = useState<LogStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null)

  const [filters, setFilters] = useState<LogFilters>({
    tipo: 'all',
    estado: 'all',
    ref_type: '',
    days: 7,
    page: 1,
    limit: 50
  })

  useEffect(() => {
    loadLogs()
  }, [filters])

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(loadLogs, 30000) // 30s
      return () => clearInterval(interval)
    }
  }, [autoRefresh, filters])

  const loadLogs = async () => {
    setLoading(true)
    try {
      const [data, statsResponse] = await Promise.all([
        listLogs(filters),
        getLogStats(filters.days)
      ])
      setLogs(data)
      setStats(statsResponse)
    } catch (error) {
      console.error('Error loading logs:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleFilterChange = (key: keyof LogFilters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value, page: key === 'page' ? value : 1 }))
  }

  const handleExport = async () => {
    try {
      const blob = await exportLogs(filters)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `logs_${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Error exporting logs:', error)
      alert('Error al exportar logs')
    }
  }

  const formatDate = (date: string) => {
    return new Date(date).toLocaleString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const getLogTypeColor = (tipo: string) => {
    switch (tipo) {
      case 'email': return 'bg-indigo-100 text-indigo-800'
      case 'whatsapp': return 'bg-green-100 text-green-800'
      case 'telegram': return 'bg-blue-100 text-blue-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusColor = (estado: string) => {
    switch (estado) {
      case 'sent': return 'bg-green-100 text-green-800'
      case 'failed': return 'bg-red-100 text-red-800'
      case 'pending': return 'bg-yellow-100 text-yellow-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="admin-shell">
      <header className="mb-6">
        <div className="admin-header">
          <h1 className="text-3xl font-bold text-gray-900">📋 Logs del Sistema</h1>
          <div className="flex gap-2">
            <label className="flex items-center gap-2 px-3 py-2 bg-white border rounded-lg cursor-pointer hover:bg-gray-50">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="text-sm">Auto-refresh (30s)</span>
            </label>
            <button
              onClick={loadLogs}
              className="btn btn-primary"
              disabled={loading}
            >
              {loading ? '⏳' : '🔄'} Actualizar
            </button>
            <button
              onClick={handleExport}
              className="btn"
            >
              📥 Exportar CSV
            </button>
          </div>
        </div>
      </header>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="card">
            <div className="text-sm text-gray-600 mb-1">Total enviados (últimos {stats.period_days} días)</div>
            <div className="text-2xl font-bold text-blue-600">{stats.total}</div>
          </div>
          <div className="card">
            <div className="text-sm text-gray-600 mb-1">Enviados</div>
            <div className="text-2xl font-bold text-green-600">{stats.by_status?.sent || 0}</div>
          </div>
          <div className="card">
            <div className="text-sm text-gray-600 mb-1">Fallidos</div>
            <div className="text-2xl font-bold text-red-600">{stats.by_status?.failed || 0}</div>
          </div>
          <div className="card">
            <div className="text-sm text-gray-600 mb-1">Distribución por tipo</div>
            <div className="text-sm text-gray-900">
              {Object.entries(stats.by_tipo || {}).map(([tipo, count]) => (
                <span key={tipo} className="mr-2 font-medium">
                  {tipo}: {count}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="card mb-6">
        <h3 className="font-semibold mb-3 text-gray-900">🔍 Filtros</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tipo de canal
            </label>
            <select
              value={filters.tipo}
              onChange={(e) => handleFilterChange('tipo', e.target.value)}
              className="input"
            >
              <option value="all">Todos</option>
              <option value="email">Email</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="telegram">Telegram</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Estado
            </label>
            <select
              value={filters.estado}
              onChange={(e) => handleFilterChange('estado', e.target.value)}
              className="input"
            >
              <option value="all">Todos</option>
              <option value="sent">Enviados</option>
              <option value="failed">Fallidos</option>
              <option value="pending">Pendientes</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tipo de referencia
            </label>
            <input
              type="text"
              value={filters.ref_type}
              onChange={(e) => handleFilterChange('ref_type', e.target.value)}
              placeholder="invoice, stock_alert..."
              className="input"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Días hacia atrás
            </label>
            <input
              type="number"
              min={1}
              max={90}
              value={filters.days}
              onChange={(e) => handleFilterChange('days', Number(e.target.value))}
              className="input"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Registros por página
            </label>
            <input
              type="number"
              min={10}
              max={500}
              step={10}
              value={filters.limit}
              onChange={(e) => handleFilterChange('limit', Number(e.target.value))}
              className="input"
            />
          </div>
        </div>
      </div>

      {/* Logs Table */}
      <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
        {loading && logs.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <div className="animate-spin inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mb-2"></div>
            <div>Cargando logs...</div>
          </div>
        ) : logs.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No se encontraron logs con los filtros aplicados
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Fecha/Hora
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Tipo
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Tipo
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Estado
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Canal
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Destinatario
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Asunto / Mensaje
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Referencia
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Detalles
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {logs.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                        {formatDate(log.created_at)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-medium rounded ${getLogTypeColor(log.tipo)}`}>
                          {log.tipo}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-medium rounded ${getStatusColor(log.estado)}`}>
                          {log.estado}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {log.canal || '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 font-medium">
                        {log.destinatario}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {log.asunto || log.mensaje?.slice(0, 80) || '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {log.ref_type ? `${log.ref_type}${log.ref_id ? ` · ${log.ref_id.slice(0, 6)}` : ''}` : '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm">
                        <button
                          onClick={() => setSelectedLog(log)}
                          className="text-blue-600 hover:text-blue-800 font-medium"
                        >
                          Ver JSON
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="bg-gray-50 px-4 py-3 border-t border-gray-200 flex items-center justify-between">
              <div className="text-sm text-gray-700">
                Mostrando <span className="font-medium">{logs.length}</span> registros (últimos {filters.days} días)
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleFilterChange('page', Math.max(1, filters.page - 1))}
                  disabled={filters.page === 1}
                  className="px-3 py-1 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  ← Anterior
                </button>
                <span className="px-3 py-1 bg-white border border-gray-300 rounded-lg">
                  Página {filters.page}
                </span>
                <button
                  onClick={() => handleFilterChange('page', filters.page + 1)}
                  disabled={logs.length < filters.limit}
                  className="px-3 py-1 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Siguiente →
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Modal Detalles */}
      {selectedLog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden">
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold">Detalles del Log</h3>
              <button
                onClick={() => setSelectedLog(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>
            <div className="p-4 overflow-y-auto max-h-[calc(90vh-80px)]">
              <pre className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto text-sm font-mono">
                {JSON.stringify(selectedLog, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

