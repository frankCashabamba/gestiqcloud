/**
 * Hook para obtener KPIs del dashboard en tiempo real
 * Consumidor del endpoint /api/v1/dashboard/kpis
 */

import { useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthContext'

export interface DashboardKPIs {
  periodo: string
  fecha_inicio: string | null
  fecha_fin: string
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
      const response = await fetch(`/api/v1/dashboard/kpis`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`)
      }

      const result = await response.json()
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar KPIs')
      console.error('Error fetching dashboard KPIs:', err)
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
        const response = await fetch('/api/v1/dashboard/kpis?sector=taller', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        })

        if (!response.ok) {
          throw new Error(`Error ${response.status}`)
        }

        const result = await response.json()
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
        const response = await fetch('/api/v1/dashboard/kpis?sector=panaderia', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        })

        if (!response.ok) {
          throw new Error(`Error ${response.status}`)
        }

        const result = await response.json()
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
export function formatCurrency(value: number, currency: string = 'EUR'): string {
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

/**
 * Formateador de números profesional
 */
export function formatNumber(value: number): string {
  return new Intl.NumberFormat('es-ES').format(value)
}
