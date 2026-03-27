/**
 * LogsViewer.tsx
 * Dos tabs: Notificaciones (email/whatsapp/telegram) y Auditoría (create/update/delete)
 */

import React, { useState, useEffect, useCallback } from 'react'

import { useAuthGuard } from '../hooks/useAuthGuard'
import { listLogs, exportLogs, getLogStats, listAuditEvents, getAuditStats } from '../services/logs'

import type { LogEntry, LogFilters, LogStats, AuditEntry, AuditFilters, AuditStats } from '../types/logs'

type Tab = 'notifications' | 'audit'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function formatDate(date: string) {
  return new Date(date).toLocaleString('es-ES', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

const ACTION_COLORS: Record<string, string> = {
  create: 'bg-green-100 text-green-800',
  update: 'bg-blue-100 text-blue-800',
  delete: 'bg-red-100 text-red-800',
}

const ACTION_ICONS: Record<string, string> = {
  create: '✚',
  update: '✎',
  delete: '✕',
}

const NOTIF_TYPE_COLORS: Record<string, string> = {
  email: 'bg-indigo-100 text-indigo-800',
  whatsapp: 'bg-green-100 text-green-800',
  telegram: 'bg-blue-100 text-blue-800',
}

const STATUS_COLORS: Record<string, string> = {
  sent: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  pending: 'bg-yellow-100 text-yellow-800',
}

function Badge({ text, colorClass }: { text: string; colorClass: string }) {
  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded ${colorClass}`}>
      {text}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Tab: Auditoría
// ---------------------------------------------------------------------------
function AuditTab() {
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [stats, setStats] = useState<AuditStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<AuditEntry | null>(null)

  const [filters, setFilters] = useState<AuditFilters>({
    tenant_id: '',
    action: 'all',
    entity_type: 'all',
    search: '',
    days: 7,
    page: 1,
    limit: 50,
  })

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [data, s] = await Promise.all([
        listAuditEvents(filters),
        getAuditStats({ tenant_id: filters.tenant_id, days: filters.days }),
      ])
      setEntries(data)
      setStats(s)
    } catch (e) {
      console.error('Error cargando auditoría:', e)
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => { load() }, [load])

  const set = (key: keyof AuditFilters, value: any) =>
    setFilters(prev => ({ ...prev, [key]: value, page: key === 'page' ? value : 1 }))

  const entityTypes = stats
    ? Object.keys(stats.by_entity_type).sort()
    : []

  return (
    <div>
      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="card">
            <div className="text-xs text-gray-500 mb-1">Total acciones ({stats.period_days}d)</div>
            <div className="text-2xl font-bold text-gray-900">{stats.total.toLocaleString()}</div>
          </div>
          <div className="card">
            <div className="text-xs text-gray-500 mb-1">Creaciones</div>
            <div className="text-2xl font-bold text-green-600">{stats.by_action.create ?? 0}</div>
          </div>
          <div className="card">
            <div className="text-xs text-gray-500 mb-1">Actualizaciones</div>
            <div className="text-2xl font-bold text-blue-600">{stats.by_action.update ?? 0}</div>
          </div>
          <div className="card">
            <div className="text-xs text-gray-500 mb-1">Eliminaciones</div>
            <div className="text-2xl font-bold text-red-600">{stats.by_action.delete ?? 0}</div>
          </div>
        </div>
      )}

      {/* Top tenants */}
      {stats && stats.by_tenant.length > 0 && !filters.tenant_id && (
        <div className="card mb-6">
          <div className="text-xs font-semibold text-gray-500 uppercase mb-2">Tenants más activos</div>
          <div className="flex flex-wrap gap-2">
            {stats.by_tenant.map(t => (
              <button
                key={t.tenant_id ?? 'sistema'}
                onClick={() => set('tenant_id', t.tenant_id ?? '')}
                className="px-3 py-1 bg-gray-100 hover:bg-blue-100 hover:text-blue-700 rounded-full text-sm transition-colors"
              >
                {t.tenant_name ?? t.tenant_id ?? 'sistema'}
                <span className="ml-1 font-bold">{t.total}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Filtros */}
      <div className="card mb-6">
        <h3 className="font-semibold mb-3 text-gray-900">Filtros</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="lg:col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Tenant ID (UUID o nombre)</label>
            <input
              type="text"
              value={filters.tenant_id}
              onChange={e => set('tenant_id', e.target.value.trim())}
              placeholder="Pegar UUID del tenant…"
              className="input font-mono text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Acción</label>
            <select value={filters.action} onChange={e => set('action', e.target.value)} className="input">
              <option value="all">Todas</option>
              <option value="create">Crear</option>
              <option value="update">Actualizar</option>
              <option value="delete">Eliminar</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Entidad</label>
            <select value={filters.entity_type} onChange={e => set('entity_type', e.target.value)} className="input">
              <option value="all">Todas</option>
              {entityTypes.map(et => (
                <option key={et} value={et}>{et}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Días hacia atrás</label>
            <input
              type="number" min={1} max={365}
              value={filters.days}
              onChange={e => set('days', Number(e.target.value))}
              className="input"
            />
          </div>
        </div>
        <div className="mt-3 flex gap-3 items-center">
          <input
            type="text"
            value={filters.search}
            onChange={e => set('search', e.target.value)}
            placeholder="Buscar por ID de entidad o tipo…"
            className="input flex-1"
          />
          {filters.tenant_id && (
            <button
              onClick={() => set('tenant_id', '')}
              className="text-sm text-gray-500 hover:text-red-600"
            >
              Limpiar tenant
            </button>
          )}
        </div>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
        {loading && entries.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <div className="animate-spin inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mb-2" />
            <div>Cargando auditoría…</div>
          </div>
        ) : entries.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            Sin resultados con los filtros aplicados
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {['Fecha/Hora', 'Tenant', 'Acción', 'Entidad', 'ID Entidad', 'Usuario', 'IP', 'Cambios'].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {entries.map(ev => (
                    <tr key={ev.id} className="hover:bg-gray-50">
                      <td className="px-4 py-2 whitespace-nowrap text-gray-700">{formatDate(ev.created_at)}</td>
                      <td className="px-4 py-2 whitespace-nowrap">
                        {ev.tenant_name ? (
                          <button
                            className="text-blue-600 hover:underline font-medium"
                            onClick={() => set('tenant_id', ev.tenant_id ?? '')}
                            title={ev.tenant_id ?? ''}
                          >
                            {ev.tenant_name}
                          </button>
                        ) : (
                          <span className="text-gray-400 text-xs font-mono">
                            {ev.tenant_id?.slice(0, 8) ?? 'sistema'}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2 whitespace-nowrap">
                        <Badge
                          text={`${ACTION_ICONS[ev.action] ?? ''} ${ev.action}`}
                          colorClass={ACTION_COLORS[ev.action] ?? 'bg-gray-100 text-gray-700'}
                        />
                      </td>
                      <td className="px-4 py-2 whitespace-nowrap text-gray-900 font-medium">{ev.entity_type}</td>
                      <td className="px-4 py-2 whitespace-nowrap font-mono text-xs text-gray-500">
                        {ev.entity_id ? ev.entity_id.slice(0, 12) + (ev.entity_id.length > 12 ? '…' : '') : '—'}
                      </td>
                      <td className="px-4 py-2 whitespace-nowrap font-mono text-xs text-gray-500">
                        {ev.user_id ? ev.user_id.slice(0, 8) + '…' : (
                          <span className="text-gray-400">sistema</span>
                        )}
                      </td>
                      <td className="px-4 py-2 whitespace-nowrap text-xs text-gray-400">{ev.ip ?? '—'}</td>
                      <td className="px-4 py-2 whitespace-nowrap">
                        {ev.changes && Object.keys(ev.changes).length > 0 ? (
                          <button
                            onClick={() => setSelected(ev)}
                            className="text-blue-600 hover:text-blue-800 font-medium text-xs"
                          >
                            Ver cambios ({Object.keys(ev.changes).length})
                          </button>
                        ) : (
                          <span className="text-gray-400 text-xs">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="bg-gray-50 px-4 py-3 border-t border-gray-200 flex items-center justify-between">
              <div className="text-sm text-gray-600">
                {entries.length} registros · últimos {filters.days} días
                {filters.tenant_id && <span className="ml-2 font-medium text-blue-600">· filtrado por tenant</span>}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => set('page', Math.max(1, filters.page - 1))}
                  disabled={filters.page === 1}
                  className="px-3 py-1 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed text-sm"
                >
                  ← Anterior
                </button>
                <span className="px-3 py-1 bg-white border border-gray-300 rounded text-sm">
                  Pág {filters.page}
                </span>
                <button
                  onClick={() => set('page', filters.page + 1)}
                  disabled={entries.length < filters.limit}
                  className="px-3 py-1 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed text-sm"
                >
                  Siguiente →
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Modal cambios */}
      {selected && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">
                  {ACTION_ICONS[selected.action]} {selected.action} · {selected.entity_type}
                </h3>
                <p className="text-sm text-gray-500">
                  {selected.tenant_name ?? selected.tenant_id ?? 'sistema'} · {formatDate(selected.created_at)}
                </p>
              </div>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
            </div>
            <div className="p-4 overflow-y-auto flex-1">
              {selected.changes && Object.keys(selected.changes).length > 0 ? (
                <table className="w-full text-sm border border-gray-200 rounded">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium text-gray-600 w-1/4">Campo</th>
                      <th className="px-3 py-2 text-left font-medium text-gray-600 w-[37.5%]">Antes</th>
                      <th className="px-3 py-2 text-left font-medium text-gray-600 w-[37.5%]">Después</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {Object.entries(selected.changes).map(([field, diff]) => (
                      <tr key={field} className="hover:bg-gray-50">
                        <td className="px-3 py-2 font-mono text-xs text-gray-700 font-semibold">{field}</td>
                        <td className="px-3 py-2 font-mono text-xs text-red-700 bg-red-50 break-all">
                          {diff.old === null || diff.old === undefined ? <span className="text-gray-400 italic">null</span> : String(diff.old)}
                        </td>
                        <td className="px-3 py-2 font-mono text-xs text-green-700 bg-green-50 break-all">
                          {diff.new === null || diff.new === undefined ? <span className="text-gray-400 italic">null</span> : String(diff.new)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <pre className="bg-gray-900 text-green-400 p-4 rounded text-sm font-mono overflow-x-auto">
                  {JSON.stringify(selected, null, 2)}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tab: Notificaciones (original)
// ---------------------------------------------------------------------------
function NotificationsTab() {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [stats, setStats] = useState<LogStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null)

  const [filters, setFilters] = useState<LogFilters>({
    tipo: 'all', estado: 'all', ref_type: '', days: 7, page: 1, limit: 50,
  })

  const loadLogs = useCallback(async () => {
    setLoading(true)
    try {
      const [data, statsData] = await Promise.all([listLogs(filters), getLogStats(filters.days)])
      setLogs(data)
      setStats(statsData)
    } catch (e) {
      console.error('Error loading logs:', e)
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => { loadLogs() }, [loadLogs])

  useEffect(() => {
    if (!autoRefresh) return
    const interval = setInterval(loadLogs, 30000)
    return () => clearInterval(interval)
  }, [autoRefresh, loadLogs])

  const set = (key: keyof LogFilters, value: any) =>
    setFilters(prev => ({ ...prev, [key]: value, page: key === 'page' ? value : 1 }))

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
    } catch {
      alert('Error al exportar logs')
    }
  }

  return (
    <div>
      <div className="flex justify-end gap-2 mb-4">
        <label className="flex items-center gap-2 px-3 py-2 bg-white border rounded-lg cursor-pointer hover:bg-gray-50 text-sm">
          <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)} className="w-4 h-4" />
          Auto-refresh (30s)
        </label>
        <button onClick={loadLogs} className="btn btn-primary" disabled={loading}>
          {loading ? '⏳' : '🔄'} Actualizar
        </button>
        <button onClick={handleExport} className="btn">📥 Exportar CSV</button>
      </div>

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="card">
            <div className="text-xs text-gray-500 mb-1">Total ({stats.period_days}d)</div>
            <div className="text-2xl font-bold text-blue-600">{stats.total}</div>
          </div>
          <div className="card">
            <div className="text-xs text-gray-500 mb-1">Enviados</div>
            <div className="text-2xl font-bold text-green-600">{stats.by_status?.sent ?? 0}</div>
          </div>
          <div className="card">
            <div className="text-xs text-gray-500 mb-1">Fallidos</div>
            <div className="text-2xl font-bold text-red-600">{stats.by_status?.failed ?? 0}</div>
          </div>
          <div className="card">
            <div className="text-xs text-gray-500 mb-1">Por tipo</div>
            <div className="text-sm text-gray-900">
              {Object.entries(stats.by_tipo ?? {}).map(([tipo, count]) => (
                <span key={tipo} className="mr-2">{tipo}: <strong>{count}</strong></span>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="card mb-6">
        <h3 className="font-semibold mb-3 text-gray-900">Filtros</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Canal</label>
            <select value={filters.tipo} onChange={e => set('tipo', e.target.value)} className="input">
              <option value="all">Todos</option>
              <option value="email">Email</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="telegram">Telegram</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Estado</label>
            <select value={filters.estado} onChange={e => set('estado', e.target.value)} className="input">
              <option value="all">Todos</option>
              <option value="sent">Enviados</option>
              <option value="failed">Fallidos</option>
              <option value="pending">Pendientes</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Ref. tipo</label>
            <input type="text" value={filters.ref_type} onChange={e => set('ref_type', e.target.value)} placeholder="invoice, stock_alert…" className="input" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Días</label>
            <input type="number" min={1} max={90} value={filters.days} onChange={e => set('days', Number(e.target.value))} className="input" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Por página</label>
            <input type="number" min={10} max={500} step={10} value={filters.limit} onChange={e => set('limit', Number(e.target.value))} className="input" />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
        {loading && logs.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <div className="animate-spin inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mb-2" />
            <div>Cargando…</div>
          </div>
        ) : logs.length === 0 ? (
          <div className="p-8 text-center text-gray-500">Sin resultados</div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {['Fecha/Hora', 'Tipo', 'Estado', 'Canal', 'Destinatario', 'Asunto', 'Referencia', 'Detalles'].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {logs.map(log => (
                    <tr key={log.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 whitespace-nowrap text-gray-900">{formatDate(log.created_at)}</td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <Badge text={log.tipo} colorClass={NOTIF_TYPE_COLORS[log.tipo] ?? 'bg-gray-100 text-gray-700'} />
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <Badge text={log.estado} colorClass={STATUS_COLORS[log.estado] ?? 'bg-gray-100 text-gray-700'} />
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-gray-600">{log.canal ?? '—'}</td>
                      <td className="px-4 py-3 whitespace-nowrap font-medium text-gray-900">{log.destinatario}</td>
                      <td className="px-4 py-3 whitespace-nowrap text-gray-600">{log.asunto ?? log.mensaje?.slice(0, 60) ?? '—'}</td>
                      <td className="px-4 py-3 whitespace-nowrap text-gray-600">
                        {log.ref_type ? `${log.ref_type}${log.ref_id ? ` · ${log.ref_id.slice(0, 6)}` : ''}` : '—'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <button onClick={() => setSelectedLog(log)} className="text-blue-600 hover:text-blue-800 font-medium text-sm">
                          Ver JSON
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="bg-gray-50 px-4 py-3 border-t flex items-center justify-between">
              <div className="text-sm text-gray-600">{logs.length} registros · últimos {filters.days} días</div>
              <div className="flex gap-2">
                <button onClick={() => set('page', Math.max(1, filters.page - 1))} disabled={filters.page === 1}
                  className="px-3 py-1 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40 text-sm">← Anterior</button>
                <span className="px-3 py-1 bg-white border border-gray-300 rounded text-sm">Pág {filters.page}</span>
                <button onClick={() => set('page', filters.page + 1)} disabled={logs.length < filters.limit}
                  className="px-3 py-1 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40 text-sm">Siguiente →</button>
              </div>
            </div>
          </>
        )}
      </div>

      {selectedLog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden">
            <div className="p-4 border-b flex items-center justify-between">
              <h3 className="text-lg font-semibold">Detalles del Log</h3>
              <button onClick={() => setSelectedLog(null)} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
            </div>
            <div className="p-4 overflow-y-auto max-h-[calc(90vh-80px)]">
              <pre className="bg-gray-900 text-green-400 p-4 rounded text-sm font-mono overflow-x-auto">
                {JSON.stringify(selectedLog, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Página principal
// ---------------------------------------------------------------------------
export default function LogsViewer() {
  useAuthGuard('superadmin')
  const [tab, setTab] = useState<Tab>('audit')

  return (
    <div className="admin-shell">
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Logs del Sistema</h1>
      </header>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 mb-6">
        <button
          onClick={() => setTab('audit')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            tab === 'audit'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Auditoría de acciones
        </button>
        <button
          onClick={() => setTab('notifications')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            tab === 'notifications'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Notificaciones
        </button>
      </div>

      {tab === 'audit' ? <AuditTab /> : <NotificationsTab />}
    </div>
  )
}
