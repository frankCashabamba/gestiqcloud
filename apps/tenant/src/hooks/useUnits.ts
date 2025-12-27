/**
 * useUnits Hook
 *
 * Hook React para cargar y cachear unidades de medida dinámicamente.
 * Reemplaza hardcoding de getSectorUnits() en sectorHelpers.ts
 *
 * Soporta:
 * - Caching automático (5 minutos)
 * - Loading state
 * - Error handling con fallback
 *
 * Uso:
 * ```tsx
 * const { units, loading, error } = useUnits('panaderia')
 *
 * if (loading) return <div>Cargando...</div>
 *
 * return (
 *   <select>
 *     {units.map(unit => (
 *       <option key={unit.code} value={unit.code}>
 *         {unit.label}
 *       </option>
 *     ))}
 *   </select>
 * )
 * ```
 */

import { useEffect, useState } from 'react'
import { useTenantConfig } from '../contexts/TenantConfigContext'
import {
  getSectorUnits,
  getDefaultUnits,
  type Unit,
} from '../services/unitService'

interface UseUnitsState {
  units: Unit[]
  loading: boolean
  error: string | null
}

// Cache global para unidades por sector
const unitsCache: Map<
  string,
  {
    data: Unit[]
    timestamp: number
  }
> = new Map()

const CACHE_TTL = 5 * 60 * 1000 // 5 minutos

/**
 * Hook para cargar unidades del sector actual
 *
 * Automáticamente detecta el sector del tenant config
 */
export function useUnits(): UseUnitsState {
  const { config } = useTenantConfig()
  const [state, setState] = useState<UseUnitsState>({
    units: getDefaultUnits(),
    loading: true,
    error: null,
  })

  useEffect(() => {
    const loadUnits = async () => {
      try {
        const sectorCode = config?.sector?.plantilla || config?.tenant?.plantilla_inicio

        if (!sectorCode) {
          // Sin sector configurado, usar defaults
          setState({
            units: getDefaultUnits(),
            loading: false,
            error: null,
          })
          return
        }

        // Verificar cache
        const cached = unitsCache.get(sectorCode)
        if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
          setState({
            units: cached.data,
            loading: false,
            error: null,
          })
          return
        }

        // Cargar desde API
        setState(prev => ({ ...prev, loading: true }))

        const units = await getSectorUnits(sectorCode)

        // Guardar en cache
        unitsCache.set(sectorCode, {
          data: units,
          timestamp: Date.now(),
        })

        setState({
          units,
          loading: false,
          error: null,
        })
      } catch (err: any) {
        const errorMessage =
          err?.message || 'Error cargando unidades de medida'

        console.error('[useUnits]', errorMessage)

        setState({
          units: getDefaultUnits(),
          loading: false,
          error: errorMessage,
        })
      }
    }

    loadUnits()
  }, [config?.sector?.plantilla, config?.tenant?.plantilla_inicio])

  return state
}

/**
 * Hook alternativo: cargar unidades de un sector específico
 *
 * @param sectorCode - Código del sector (ej: 'panaderia')
 */
export function useUnitsBySector(sectorCode: string | null | undefined) {
  const [units, setUnits] = useState<Unit[]>(getDefaultUnits())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!sectorCode) {
      setUnits(getDefaultUnits())
      return
    }

    const loadUnits = async () => {
      // Verificar cache primero
      const cached = unitsCache.get(sectorCode)
      if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
        setUnits(cached.data)
        setLoading(false)
        return
      }

      setLoading(true)
      setError(null)

      try {
        const loadedUnits = await getSectorUnits(sectorCode)

        // Guardar en cache
        unitsCache.set(sectorCode, {
          data: loadedUnits,
          timestamp: Date.now(),
        })

        setUnits(loadedUnits)
      } catch (err: any) {
        const errorMessage = err?.message || 'Error loading units'
        setError(errorMessage)
        setUnits(getDefaultUnits())
      } finally {
        setLoading(false)
      }
    }

    loadUnits()
  }, [sectorCode])

  return { units, loading, error }
}

/**
 * Limpiar cache manualmente si es necesario
 */
export function clearUnitsCache() {
  unitsCache.clear()
}

/**
 * Limpiar cache de un sector específico
 */
export function clearUnitsCacheForSector(sectorCode: string) {
  unitsCache.delete(sectorCode)
}
