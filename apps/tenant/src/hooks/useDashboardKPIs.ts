/**
 * Hook para obtener KPIs del dashboard en tiempo real
 * Consumidor del endpoint /api/v1/dashboard/kpis
 */

import { useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { apiFetch } from '../lib/http'

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
  ordenes_trabajo_activas: number
  servicios_completados_hoy: number
  repuestos_pendientes: number
}

export interface PanaderiaKPIs {
  ventas_mostrador: number
  stock_critico: number
  mermas_registradas: number
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

  return normalized
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

    try {
      setError(null)
      const result = await apiFetch<DashboardKPIs>('/api/v1/dashboard/kpis', { authToken: token })
      setData(normalizeKPIs(result))
    } catch (err) {
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

    const fetchTallerKPIs = async () => {
      try {
        const result = await apiFetch<TallerKPIs>('/api/v1/dashboard/kpis?sector=taller', {
          authToken: token,
        })
        setData(result)
      } catch (err) {
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

    const fetchPanaderiaKPIs = async () => {
      try {
        const result = await apiFetch<PanaderiaKPIs>('/api/v1/dashboard/kpis?sector=panaderia', {
          authToken: token,
        })
        setData(result)
      } catch (err) {
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
