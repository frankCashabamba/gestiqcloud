/**
 * incidents.ts
 * Servicios API para incidencias y alertas de stock
 */

import type { Incident, StockAlert } from '../types/incidents'
import { API_BASE, API_ENDPOINTS } from '../constants/api'

const getAuthHeaders = () => ({
  'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
  'Content-Type': 'application/json'
})

/**
 * Lista incidencias con filtros
 */
export async function listIncidents(filters: { estado?: string }): Promise<Incident[]> {
  const params = new URLSearchParams()
  if (filters.estado) {
    params.append('estado', filters.estado)
  }

  const response = await fetch(`${API_ENDPOINTS.INCIDENTS.LIST}?${params}`, {
    headers: getAuthHeaders()
  })

  if (!response.ok) {
    throw new Error('Error al cargar incidencias')
  }

  return response.json()
}

/**
 * Obtiene detalle de una incidencia
 */
export async function getIncident(id: string): Promise<Incident> {
  const response = await fetch(`${API_BASE}/admin/incidents/${id}`, {
    headers: getAuthHeaders()
  })

  if (!response.ok) {
    throw new Error('Error al cargar incidencia')
  }

  return response.json()
}

/**
 * Trigger análisis IA de una incidencia
 */
export async function analyzeIncident(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/admin/incidents/${id}/analyze`, {
    method: 'POST',
    headers: getAuthHeaders()
  })

  if (!response.ok) {
    throw new Error('Error al analizar incidencia')
  }
}

/**
 * Auto-resolver incidencia con IA
 */
export async function autoResolveIncident(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/admin/incidents/${id}/auto-resolve`, {
    method: 'POST',
    headers: getAuthHeaders()
  })

  if (!response.ok) {
    throw new Error('Error al auto-resolver incidencia')
  }
}

/**
 * Asignar incidencia a un usuario
 */
export async function assignIncident(id: string, userId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/admin/incidents/${id}/assign`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ user_id: userId })
  })

  if (!response.ok) {
    throw new Error('Error al asignar incidencia')
  }
}

/**
 * Cerrar incidencia
 */
export async function closeIncident(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/admin/incidents/${id}/close`, {
    method: 'POST',
    headers: getAuthHeaders()
  })

  if (!response.ok) {
    throw new Error('Error al cerrar incidencia')
  }
}

/**
 * Lista alertas de stock
 */
export async function listStockAlerts(filters: { estado?: string }): Promise<StockAlert[]> {
  const params = new URLSearchParams()
  if (filters.estado) {
    params.append('estado', filters.estado)
  }

  const response = await fetch(`${API_BASE}/admin/stock-alerts?${params}`, {
    headers: getAuthHeaders()
  })

  if (!response.ok) {
    throw new Error('Error al cargar alertas de stock')
  }

  return response.json()
}

/**
 * Notificar alerta de stock
 */
export async function notifyStockAlert(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/admin/stock-alerts/${id}/notify`, {
    method: 'POST',
    headers: getAuthHeaders()
  })

  if (!response.ok) {
    throw new Error('Error al notificar alerta')
  }
}

/**
 * Resolver alerta de stock
 */
export async function resolveStockAlert(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/admin/stock-alerts/${id}/resolve`, {
    method: 'POST',
    headers: getAuthHeaders()
  })

  if (!response.ok) {
    throw new Error('Error al resolver alerta')
  }
}
