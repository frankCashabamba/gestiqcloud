/**
 * logs.ts
 * Servicios API para logs del sistema
 */

import { API_ENDPOINTS, API_BASE } from '../constants/api'

import type { LogEntry, LogFilters, LogStats, AuditEntry, AuditFilters, AuditStats } from '../types/logs'

const getAdminToken = () =>
  (typeof window !== 'undefined' ? sessionStorage.getItem('access_token_admin') : null)
  || (typeof window !== 'undefined' ? localStorage.getItem('access_token') : null)

const AUTH_HEADER = () => ({
  'Authorization': `Bearer ${getAdminToken()}`,
  'Content-Type': 'application/json'
})

export async function listLogs(filters: LogFilters): Promise<LogEntry[]> {
  const params = new URLSearchParams()

  if (filters.tipo && filters.tipo !== 'all') {
    params.append('tipo', filters.tipo)
  }
  if (filters.estado && filters.estado !== 'all') {
    params.append('estado', filters.estado)
  }
  if (filters.ref_type) {
    params.append('ref_type', filters.ref_type)
  }
  if (filters.days) {
    params.append('days', filters.days.toString())
  }
  if (filters.limit) {
    params.append('limit', filters.limit.toString())
  }

  const page = Math.max(filters.page || 1, 1)
  const limit = filters.limit || 50
  const offset = (page - 1) * limit
  params.append('offset', offset.toString())

  const response = await fetch(`${API_ENDPOINTS.LOGS.LIST}?${params}`, {
    headers: AUTH_HEADER()
  })

  if (!response.ok) {
    throw new Error('Error al cargar logs')
  }

  return response.json()
}

export async function getLogStats(days: number = 30): Promise<LogStats> {
  const params = new URLSearchParams()
  params.append('days', days.toString())

  const response = await fetch(`${API_BASE}/notifications/log/stats?${params}`, {
    headers: AUTH_HEADER()
  })

  if (!response.ok) {
    throw new Error('Error al obtener estadísticas')
  }

  return response.json()
}

export async function listAuditEvents(filters: AuditFilters): Promise<AuditEntry[]> {
  const params = new URLSearchParams()
  if (filters.tenant_id) params.append('tenant_id', filters.tenant_id)
  if (filters.action && filters.action !== 'all') params.append('action', filters.action)
  if (filters.entity_type && filters.entity_type !== 'all') params.append('entity_type', filters.entity_type)
  if (filters.search) params.append('search', filters.search)
  params.append('days', filters.days.toString())
  params.append('limit', filters.limit.toString())
  params.append('offset', (Math.max(filters.page - 1, 0) * filters.limit).toString())

  const response = await fetch(`${API_BASE}/admin/logs/audit?${params}`, {
    headers: AUTH_HEADER()
  })
  if (!response.ok) throw new Error('Error al cargar auditoría')
  return response.json()
}

export async function getAuditStats(filters: Pick<AuditFilters, 'tenant_id' | 'days'>): Promise<AuditStats> {
  const params = new URLSearchParams()
  if (filters.tenant_id) params.append('tenant_id', filters.tenant_id)
  params.append('days', filters.days.toString())

  const response = await fetch(`${API_BASE}/admin/logs/audit/stats?${params}`, {
    headers: AUTH_HEADER()
  })
  if (!response.ok) throw new Error('Error al obtener estadísticas de auditoría')
  return response.json()
}

export async function exportLogs(filters: LogFilters): Promise<Blob> {
  const logs = await listLogs({
    ...filters,
    page: 1,
    limit: Math.min(filters.limit || 50, 500)
  })

  const headers = ['Date', 'Type', 'Status', 'Canal', 'Destinatario', 'Asunto', 'Referencia', 'Error']
  const escape = (value: unknown) => {
    if (value === null || value === undefined) return ''
    const str =
      typeof value === 'string'
        ? value
        : typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint'
          ? String(value)
          : JSON.stringify(value)
    return `"${(str ?? '').replace(/"/g, '""')}"`
  }

  const rows = logs.map((log) => [
    log.created_at,
    log.tipo,
    log.estado,
    log.canal || '',
    log.destinatario,
    log.asunto || '',
    log.ref_type ? `${log.ref_type}:${log.ref_id || ''}` : '',
    log.error_message || ''
  ])

  const csv = [headers, ...rows].map((row) => row.map(escape).join(',')).join('\n')
  return new Blob([csv], { type: 'text/csv;charset=utf-8;' })
}
