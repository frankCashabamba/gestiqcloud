/**
 * Hook para obtener KPIs del dashboard en tiempo real
 * Consumidor del endpoint /api/v1/dashboard/kpis
 */

import { useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { apiFetch } from '../lib/http'
import { isNetworkIssue } from '../lib/offlineHttp'
import { getOfflineCacheScope, readCachedResource, writeCachedResource } from '../lib/offlineResourceCache'

export interface DashboardKPIs {
  periodo: string
  fecha_inicio: string | null
  fecha_fin: string
  ventas_dia?: {
    total?: number
    tickets?: number
    ticket_medio?: number
    currency?: string | null
  }
  stock_rotacion?: {
    productos_alta_rotacion?: number
    productos_baja_rotacion?: number
    reposicion_necesaria?: number
  }
  comparativa_semana?: {
    actual?: number
    anterior?: number
    variacion?: number
    currency?: string | null
  }
  ventas: {
    total: number
    count: number
    mostrador: number
    promedio: number
  }
  gastos: {
    total: number
    dia: number
  }
  inventario: {
    stock_critico: number
    productos_en_stock: number
    mermas: number
  }
  facturacion: {
    por_cobrar_total: number
    por_cobrar_count: number
    vencidas: number
  }
  compras: {
    pendientes: number
  }
  pedidos: {
    pendientes: number
    entregas_hoy: number
  }
}

export interface TallerKPIs {
  pending_repairs?: {
    total?: number
    urgent?: number
    average_wait_time?: number
    time_unit?: string
  }
  monthly_revenue?: {
    current?: number
    target?: number
    progress?: number
    currency?: string
  }
  low_stock_spare_parts?: {
    items?: number
    names?: string[]
    urgency?: string
  }
  completed_jobs?: {
    today?: number
    week?: number
    month?: number
  }
  // Legacy keys for backward compatibility
  ordenes_trabajo_activas?: number
  servicios_completados_hoy?: number
  repuestos_pendientes?: number
}

export interface PanaderiaKPIs {
  counter_sales?: {
    today?: number
    yesterday?: number
    variation?: number
    currency?: string
  }
  critical_stock?: {
    items?: number
    names?: string[]
    urgency?: string
  }
  waste?: {
    today?: number
    unit?: string
    estimated_value?: number
    currency?: string
  }
  production?: {
    batches_completed?: number
    batches_scheduled?: number
    progress?: number
    orders_with_recipe?: number
  }
  ingredients_expiring?: {
    next_7_days?: number
    items?: string[]
  }
  top_products?: Array<{
    name: string
    units: number
    revenue: number
  }>
  pedidos?: {
    pendientes_cobro?: number
    pendientes_entrega?: number
  }
  // Legacy keys for backward compatibility
  ventas_mostrador?: any
  stock_critico?: any
  mermas_registradas?: any
}

interface UseDashboardKPIsOptions {
  periodo?: 'today' | 'week' | 'month' | 'year'
  autoRefresh?: boolean
  refreshInterval?: number
  enabled?: boolean
}

const normalizeKPIs = (payload: any) => {
  if (!payload || typeof payload !== 'object') return payload

  const normalized = { ...payload }

  // Retail / todoa100 backend payload -> UI expected keys
  if (payload.daily_sales && !payload.ventas_dia) {
    normalized.ventas_dia = {
      total: payload.daily_sales.total ?? 0,
      tickets: payload.daily_sales.tickets ?? 0,
      ticket_medio: payload.daily_sales.average_ticket ?? 0,
      currency: payload.daily_sales.currency,
    }
  }

  if (payload.stock_rotation && !payload.stock_rotacion) {
    normalized.stock_rotacion = {
      productos_alta_rotacion: payload.stock_rotation.high_rotation_products ?? 0,
      productos_baja_rotacion: payload.stock_rotation.low_rotation_products ?? 0,
      reposicion_necesaria: payload.stock_rotation.replenishment_needed ?? 0,
    }
  }

  if (payload.weekly_comparison && !payload.comparativa_semana) {
    const actual = payload.weekly_comparison.current ?? 0
    const anterior = payload.weekly_comparison.previous ?? 0
    const variacion =
      payload.weekly_comparison.variation ?? (anterior > 0 ? ((actual - anterior) / anterior) * 100 : 0)

    normalized.comparativa_semana = {
      actual,
      anterior,
      variacion,
      currency: payload.weekly_comparison.currency,
    }
  }

  // Taller backend payload -> UI expected keys
  if (payload.pending_repairs && !payload.reparaciones_pendientes) {
    normalized.reparaciones_pendientes = {
      total: payload.pending_repairs.total ?? 0,
      urgentes: payload.pending_repairs.urgent ?? 0,
      tiempo_medio_espera: payload.pending_repairs.average_wait_time ?? 0,
    }
  }

  if (payload.monthly_revenue && !payload.ingresos_mes) {
    normalized.ingresos_mes = {
      actual: payload.monthly_revenue.current ?? 0,
      objetivo: payload.monthly_revenue.target ?? 0,
      progreso: payload.monthly_revenue.progress ?? 0,
    }
  }

  if (payload.low_stock_spare_parts && !payload.repuestos_bajo_stock) {
    normalized.repuestos_bajo_stock = {
      items: payload.low_stock_spare_parts.items ?? 0,
      nombres: payload.low_stock_spare_parts.names ?? [],
      urgencia: payload.low_stock_spare_parts.urgency ?? 'medium',
    }
  }

  if (payload.completed_jobs && !payload.trabajos_completados) {
    normalized.trabajos_completados = {
      hoy: payload.completed_jobs.today ?? 0,
      semana: payload.completed_jobs.week ?? 0,
      mes: payload.completed_jobs.month ?? 0,
    }
  }

  // Panaderia backend payload -> UI expected keys
  if (payload.counter_sales && !payload.ventas_mostrador) {
    normalized.ventas_mostrador = {
      hoy: payload.counter_sales.today ?? 0,
      ayer: payload.counter_sales.yesterday ?? 0,
      variacion: payload.counter_sales.variation ?? 0,
      moneda: payload.counter_sales.currency,
    }
  }

  if (payload.critical_stock && !payload.stock_critico) {
    normalized.stock_critico = {
      items: payload.critical_stock.items ?? 0,
      nombres: payload.critical_stock.names ?? [],
      urgencia: payload.critical_stock.urgency ?? 'medium',
    }
  }

  if (payload.waste && !payload.mermas) {
    normalized.mermas = {
      hoy: payload.waste.today ?? 0,
      unidad: payload.waste.unit ?? 'kg',
      valor_estimado: payload.waste.estimated_value ?? 0.0,
      moneda: payload.waste.currency,
    }
  }

  if (payload.production && !payload.produccion) {
    normalized.produccion = {
      hornadas_completadas: payload.production.batches_completed ?? 0,
      hornadas_programadas: payload.production.batches_scheduled ?? 0,
      progreso: payload.production.progress ?? 0,
      pedidos_con_receta: payload.production.orders_with_recipe ?? 0,
    }
  }

  if (payload.ingredients_expiring && !payload.ingredientes_caducar) {
    normalized.ingredientes_caducar = {
      proximos_7_dias: payload.ingredients_expiring.next_7_days ?? 0,
      items: payload.ingredients_expiring.items ?? [],
    }
  }

  if (payload.top_products && !payload.top_productos) {
    normalized.top_productos = (payload.top_products || []).map((p: any) => ({
      name: p.name,
      unidades: p.units ?? 0,
      ingresos: p.revenue ?? 0,
    }))
  }

  return normalized
}

function dashboardCacheKey(scope: string) {
  return `dashboard-kpis:${getOfflineCacheScope(scope)}`
}

export function useDashboardKPIs(options: UseDashboardKPIsOptions = {}) {
  const { periodo = 'today', autoRefresh = false, refreshInterval = 60000, enabled = true } = options
  const { token } = useAuth()
  const [data, setData] = useState<DashboardKPIs | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchKPIs = async () => {
    if (!token) {
      setError('No hay sesión activa')
      setLoading(false)
      return
    }

    const cacheKey = dashboardCacheKey(`default:${periodo}`)

    try {
      setError(null)
      const result = await apiFetch<DashboardKPIs>('/api/v1/dashboard/kpis', { authToken: token })
      const normalized = normalizeKPIs(result)
      setData(normalized)
      writeCachedResource(cacheKey, normalized)
    } catch (err) {
      const cached = readCachedResource<DashboardKPIs>(cacheKey)
      if (cached && isNetworkIssue(err)) {
        setData(normalizeKPIs(cached))
        setError(null)
        return
      }
      if ((err as any)?.status === 404) {
        // Endpoint podría no estar implementado en algunas instalaciones
        setData(null)
        setError(null)
      } else {
        setError(err instanceof Error ? err.message : 'Error al cargar KPIs')
      }
      console.debug('Error fetching dashboard KPIs:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!enabled) {
      setLoading(false)
      return
    }

    fetchKPIs()

    if (autoRefresh) {
      const interval = setInterval(fetchKPIs, refreshInterval)
      return () => clearInterval(interval)
    }
  }, [periodo, token, autoRefresh, refreshInterval, enabled])

  return { data, loading, error, refetch: fetchKPIs }
}

/**
 * Hook específico para KPIs de taller mecánico
 */
export function useTallerKPIs(options: { enabled?: boolean } = {}) {
  const { enabled = true } = options
  const { token } = useAuth()
  const [data, setData] = useState<TallerKPIs | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token || !enabled) {
      setLoading(false)
      return
    }

    const cacheKey = dashboardCacheKey('taller')

    const fetchTallerKPIs = async () => {
      try {
        const result = await apiFetch<TallerKPIs>('/api/v1/dashboard/kpis?sector=taller', {
          authToken: token,
        })
        const normalized = normalizeKPIs(result)
        setData(normalized)
        writeCachedResource(cacheKey, normalized)
      } catch (err) {
        const cached = readCachedResource<TallerKPIs>(cacheKey)
        if (cached && isNetworkIssue(err)) {
          setData(normalizeKPIs(cached))
          setError(null)
          return
        }
        setError(err instanceof Error ? err.message : 'Error al cargar KPIs de taller')
      } finally {
        setLoading(false)
      }
    }

    fetchTallerKPIs()
  }, [token, enabled])

  return { data, loading, error }
}

/**
 * Hook específico para KPIs de panadería
 */
export function usePanaderiaKPIs(options: { enabled?: boolean } = {}) {
  const { enabled = true } = options
  const { token } = useAuth()
  const [data, setData] = useState<PanaderiaKPIs | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token || !enabled) {
      setLoading(false)
      return
    }

    const cacheKey = dashboardCacheKey('panaderia')

    const fetchPanaderiaKPIs = async () => {
      try {
        const result = await apiFetch<PanaderiaKPIs>('/api/v1/dashboard/kpis?sector=panaderia', {
          authToken: token,
        })
        const normalized = normalizeKPIs(result)
        setData(normalized)
        writeCachedResource(cacheKey, normalized)
      } catch (err) {
        const cached = readCachedResource<PanaderiaKPIs>(cacheKey)
        if (cached && isNetworkIssue(err)) {
          setData(normalizeKPIs(cached))
          setError(null)
          return
        }
        setError(err instanceof Error ? err.message : 'Error al cargar KPIs de panadería')
      } finally {
        setLoading(false)
      }
    }

    fetchPanaderiaKPIs()
  }, [token, enabled])

  return { data, loading, error }
}

/**
 * Formateador de moneda profesional
 */
export function formatCurrency(value: number, currency?: string | null): string {
  const curr = (currency || '').trim().toUpperCase()

  if (!curr || curr.length !== 3) {
    return new Intl.NumberFormat('es-ES', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value)
  }

  try {
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: curr,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value)
  } catch (error) {
    console.warn(`Invalid currency code: ${curr}`)
    return new Intl.NumberFormat('es-ES', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value)
  }
}

/**
 * Formateador de números profesional
 */
export function formatNumber(value: number): string {
  return new Intl.NumberFormat('es-ES').format(value)
}
