/**
 * useSectorConfig
 *
 * @deprecated Use useCompanySectorFullConfig() instead.
 * This hook is kept for backward compatibility but will be removed in the next major version.
 *
 * FASE 5: Deprecación de helpers hardcodeados
 * Timeline: Eliminación en próxima versión
 *
 * Hook para cargar la configuración completa de un sector desde la BD.
 * Reemplaza el hardcoding anterior en sectorHelpers.ts
 *
 * Proporciona:
 * - Icon (emoji)
 * - Display name
 * - Unidades de medida
 * - Reglas de formateo
 * - Configuración de impresión
 * - Campos requeridos
 *
 * Uso (DEPRECATED):
 * ```tsx
 * // ❌ ANTERIOR (DEPRECATED)
 * const { config } = useSectorConfig('panaderia')
 *
 * // ✅ NUEVO (USE THIS)
 * const { sectorConfig } = useCompanySectorFullConfig('panaderia')
 * ```
 */

import { useEffect, useState, useCallback } from 'react'
import tenantApi from '../shared/api/client'

export interface SectorUnit {
  code: string
  label: string
}

export interface FormatRule {
  decimals?: number
  suffix?: string
  metric?: string
}

export interface BrandingConfig {
  // Legacy
  color_primario: string
  logo?: string | null
  plantilla_inicio: string
  dashboard_template: string

  // Nuevo (reemplaza sectorHelpers.ts)
  icon: string
  displayName: string
  units: SectorUnit[]
  format_rules: Record<string, FormatRule>
  print_config: {
    width: number
    fontSize: number
    showLogo: boolean
    showDetails: boolean
  }
  required_fields: Record<string, string[]>
}

export interface SectorConfigResponse {
  ok: boolean
  code: string
  sector_name: string
  branding: BrandingConfig
}

interface UseSectorConfigState {
  config: BrandingConfig | null
  loading: boolean
  error: string | null
}

// Cache para evitar múltiples peticiones
const configCache = new Map<string, BrandingConfig>()
const CACHE_TTL = 5 * 60 * 1000 // 5 minutos

export function useSectorConfig(sector: string | null | undefined): UseSectorConfigState {
  const [state, setState] = useState<UseSectorConfigState>({
    config: null,
    loading: false,
    error: null,
  })

  const loadConfig = useCallback(async () => {
    if (!sector) {
      setState({ config: null, loading: false, error: null })
      return
    }

    // Verificar cache
    if (configCache.has(sector)) {
      setState({
        config: configCache.get(sector)!,
        loading: false,
        error: null,
      })
      return
    }

    setState({ config: null, loading: true, error: null })

    try {
      const encodedSector = encodeURIComponent(sector)
      const response = await tenantApi.get<SectorConfigResponse>(
        `/api/v1/sectors/${encodedSector}/config`
      )

      const branding = response.data.branding

      // Guardar en cache
      configCache.set(sector, branding)

      setState({
        config: branding,
        loading: false,
        error: null,
      })
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail ||
        err.message ||
        `Error cargando configuración del sector '${sector}'`

      console.error('[useSectorConfig]', errorMessage)

      setState({
        config: null,
        loading: false,
        error: errorMessage,
      })
    }
  }, [sector])

  useEffect(() => {
    loadConfig()
  }, [loadConfig])

  return state
}

/**
 * Helpers derivados de la configuración del sector
 * (reemplazan funciones de sectorHelpers.ts)
 */

export function getSectorIcon(config: BrandingConfig | null): string {
  return config?.icon || '🏢'
}

export function getSectorColor(config: BrandingConfig | null): string {
  return config?.color_primario || '#6366f1'
}

export function getSectorDisplayName(config: BrandingConfig | null): string {
  return config?.displayName || 'General'
}

export function getSectorUnits(config: BrandingConfig | null): SectorUnit[] {
  return config?.units || [
    { code: 'unit', label: 'Unidad' },
    { code: 'kg', label: 'Kilogramo' },
    { code: 'l', label: 'Litro' },
  ]
}

export function getFormatRule(
  config: BrandingConfig | null,
  type: string
): FormatRule {
  return config?.format_rules?.[type] || {}
}

export function getPrintConfig(config: BrandingConfig | null) {
  return (
    config?.print_config || {
      width: 58,
      fontSize: 10,
      showLogo: true,
      showDetails: false,
    }
  )
}

export function getRequiredFields(
  config: BrandingConfig | null,
  context: string
): string[] {
  return config?.required_fields?.[context] || []
}

/**
 * Hook alternativo: cargar múltiples sectores
 */
export function useSectorConfigs(sectors: string[]) {
  const [configs, setConfigs] = useState<Map<string, BrandingConfig>>(new Map())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadConfigs = async () => {
      setLoading(true)
      setError(null)

      const newConfigs = new Map<string, BrandingConfig>()

      try {
        for (const sector of sectors) {
          // Usar cache si disponible
          if (configCache.has(sector)) {
            newConfigs.set(sector, configCache.get(sector)!)
            continue
          }

          try {
            const encodedSector = encodeURIComponent(sector)
            const response = await tenantApi.get<SectorConfigResponse>(
              `/api/v1/sectors/${encodedSector}/config`
            )
            newConfigs.set(sector, response.data.branding)
            configCache.set(sector, response.data.branding)
          } catch (err) {
            console.warn(`Error cargando configuración del sector '${sector}'`, err)
          }
        }

        setConfigs(newConfigs)
      } catch (err: any) {
        setError(err.message || 'Error cargando configuraciones')
      } finally {
        setLoading(false)
      }
    }

    if (sectors.length > 0) {
      loadConfigs()
    }
  }, [sectors])

  return { configs, loading, error }
}

/**
 * Clearear cache manualmente si es necesario
 */
export function clearSectorConfigCache() {
  configCache.clear()
}
