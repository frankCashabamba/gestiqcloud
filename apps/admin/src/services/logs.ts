/**
 * logs.ts
 * Servicios API para logs del sistema
 */

import type { LogEntry, LogFilters, LogStats } from '../types/logs'
import { API_ENDPOINTS, API_BASE } from '../constants/api'

const AUTH_HEADER = () => ({
  'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
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

export async function exportLogs(filters: LogFilters): Promise<Blob> {
  const logs = await listLogs({
    ...filters,
    page: 1,
    limit: Math.min(filters.limit || 50, 500)
  })

  const headers = ['Date', 'Type', 'Status', 'Canal', 'Destinatario', 'Asunto', 'Referencia', 'Error']
  const escape = (value: unknown) => {
    if (value === null || value === undefined) return ''
    const str = String(value).replace(/"/g, '""')
    return `"${str}"`
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
