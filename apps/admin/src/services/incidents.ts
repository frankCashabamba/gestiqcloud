/**
 * incidents.ts
 * Servicios API para incidencias y alertas de stock
 */

import { API_BASE, API_ENDPOINTS } from '../constants/api'
import { apiFetch } from '../lib/http'
import { authManager } from '../lib/auth'

import type { Incident, StockAlert } from '../types/incidents'

type RawIncident = {
  id: string
  tenant_id?: string | null
  type?: string | null
  severity?: 'low' | 'medium' | 'high' | 'critical' | null
  title?: string | null
  description?: string | null
  stack_trace?: string | null
  context?: Record<string, unknown> | null
  status?: 'open' | 'in_progress' | 'resolved' | 'closed' | null
  auto_detected?: boolean
  auto_resolved?: boolean
  ia_analysis?: string | Record<string, unknown> | null
  ia_suggestion?: string | null
  assigned_to?: string | null
  created_at: string
  updated_at: string
  resolved_at?: string | null
}

type RawStockAlert = {
  id: string
  tenant_id: string
  product_id: string
  warehouse_id?: string | null
  current_qty?: number | null
  threshold_qty?: number | null
  status?: 'active' | 'acknowledged' | 'resolved' | null
  created_at: string
  notified_at?: string | null
  resolved_at?: string | null
}

function normalizeIncident(raw: RawIncident): Incident {
  return {
    id: String(raw.id),
    tenant_id: raw.tenant_id ? String(raw.tenant_id) : undefined,
    tipo: String(raw.type || ''),
    severidad: (raw.severity || 'low') as Incident['severidad'],
    titulo: String(raw.title || ''),
    description: String(raw.description || ''),
    estado: (raw.status || 'open') as Incident['estado'],
    auto_detected: Boolean(raw.auto_detected),
    auto_resolved: Boolean(raw.auto_resolved),
    stack_trace: raw.stack_trace || undefined,
    metadata: (raw.context as Record<string, any> | null) || undefined,
    ia_analysis: (raw.ia_analysis as Incident['ia_analysis']) || undefined,
    ia_suggestion: raw.ia_suggestion || undefined,
    assigned_to: raw.assigned_to || undefined,
    created_at: raw.created_at,
    updated_at: raw.updated_at,
    resolved_at: raw.resolved_at || undefined,
  }
}

function normalizeStockAlert(raw: RawStockAlert): StockAlert {
  return {
    id: String(raw.id),
    tenant_id: String(raw.tenant_id),
    product_id: String(raw.product_id),
    product_name: String(raw.product_id),
    warehouse_id: String(raw.warehouse_id || ''),
    warehouse_name: raw.warehouse_id ? String(raw.warehouse_id) : 'Sin almacén',
    qty_on_hand: Number(raw.current_qty || 0),
    min_qty: Number(raw.threshold_qty || 0),
    estado: (
      raw.status === 'acknowledged' ? 'notified' : (raw.status || 'active')
    ) as StockAlert['estado'],
    detected_at: raw.created_at,
    notified_at: raw.notified_at || undefined,
    resolved_at: raw.resolved_at || undefined,
  }
}

/**
 * Lista incidencias con filtros
 */
export async function listIncidents(filters: { estado?: string; tenant_id?: string }): Promise<Incident[]> {
  const params = new URLSearchParams()
  if (filters.estado) {
    params.append('status', filters.estado)
  }
  if (filters.tenant_id) {
    params.append('tenant_id', filters.tenant_id)
  }

  const data = await apiFetch<RawIncident[]>(`${API_ENDPOINTS.INCIDENTS.LIST}?${params.toString()}`)
  return data.map(normalizeIncident)
}

/**
 * Obtiene detalle de una incidencia
 */
export async function getIncident(id: string): Promise<Incident> {
  const data = await apiFetch<RawIncident>(`${API_BASE}/admin/incidents/${id}`)
  return normalizeIncident(data)
}

/**
 * Trigger análisis IA de una incidencia y devuelve el detalle actualizado
 */
export async function analyzeIncident(id: string): Promise<Incident> {
  await apiFetch(`${API_BASE}/admin/incidents/${id}/analyze`, {
    method: 'POST',
    body: JSON.stringify({
      use_gpt4: false,
      include_code_suggestions: true,
    }),
  })
  return getIncident(id)
}

/**
 * Auto-resolver incidencia con IA y devuelve el detalle actualizado
 */
export async function autoResolveIncident(id: string): Promise<Incident> {
  await apiFetch(`${API_BASE}/admin/incidents/${id}/resolve`, {
    method: 'POST',
  })
  return getIncident(id)
}

/**
 * Asignar incidencia a un usuario
 */
export async function assignIncident(id: string, userId: string): Promise<Incident> {
  const data = await apiFetch<RawIncident>(`${API_BASE}/admin/incidents/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ assigned_to: userId, status: 'in_progress' }),
  })
  return normalizeIncident(data)
}

/**
 * Cerrar incidencia
 */
export async function closeIncident(id: string): Promise<Incident> {
  const data = await apiFetch<RawIncident>(`${API_BASE}/admin/incidents/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ status: 'closed' }),
  })
  return normalizeIncident(data)
}

/**
 * Lista alertas de stock
 */
export async function listStockAlerts(filters: { estado?: string; tenant_id?: string }): Promise<StockAlert[]> {
  const params = new URLSearchParams()
  if (filters.estado) {
    params.append('status', filters.estado)
  }
  if (filters.tenant_id) {
    params.append('tenant_id', filters.tenant_id)
  }

  const data = await apiFetch<RawStockAlert[]>(`${API_BASE}/admin/incidents/stock-alerts?${params.toString()}`)
  return data.map(normalizeStockAlert)
}

/**
 * Notificar alerta de stock
 */
export async function notifyStockAlert(id: string): Promise<void> {
  await apiFetch(`${API_BASE}/admin/incidents/stock-alerts/${id}/notify`, {
    method: 'POST',
  })
}

/**
 * Resolver alerta de stock
 */
export async function resolveStockAlert(id: string): Promise<void> {
  await apiFetch(`${API_BASE}/admin/incidents/stock-alerts/${id}/resolve`, {
    method: 'POST',
  })
}
