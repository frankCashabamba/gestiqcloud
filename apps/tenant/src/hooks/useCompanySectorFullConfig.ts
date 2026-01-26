/**
 * useCompanySectorFullConfig
 *
 * Hook para cargar configuración COMPLETA de un sector desde la BD.
 * Reemplaza hardcoding anterior en sectorHelpers.ts y entityTypes.ts
 *
 * Proporciona:
 * - Branding (icon, color, name)
 * - Features (expiry_tracking, lot_tracking, etc.)
 * - Fields (aliases, validations, placeholders)
 * - Defaults (categorías, impuestos, etc.)
 * - Endpoints (URLs dinámicas)
 * - Templates (permitidos)
 *
 * Usa endpoint: GET /api/v1/sectors/{code}/full-config
 *
 * Uso:
 * ```tsx
 * const { config, loading, error } = useCompanySectorFullConfig('panaderia')
 *
 * if (loading) return <div>Cargando...</div>
 * if (error) return <div>{error}</div>
 *
 * return (
 *   <div>
 *     <span>{config.branding.icon}</span>
 *     <span>{config.branding.displayName}</span>
 *   </div>
 * )
 * ```
 */

import { useEffect, useState, useCallback } from 'react'
import tenantApi from '../shared/api/client'

// ============================================================================
// INTERFACES
// ============================================================================

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
  icon: string
  displayName: string
  color_primario: string
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

export interface FieldsConfig {
  [module: string]: {
    aliases: Record<string, string[]>
    validations: Record<string, string>
    placeholders: Record<string, string>
  }
}

export interface FeaturesConfig {
  expiry_tracking: boolean
  lot_tracking: boolean
  serial_tracking: boolean
  batch_tracking: boolean
  weight_tracking: boolean
  [key: string]: boolean
}

export interface DefaultsConfig {
  categories: string[]
  tax_rate: number | null
  currency: string | null
  locale: string
  timezone: string
  price_includes_tax: boolean
}

export interface EndpointsConfig {
  imports: string
  products: string
  customers: string
  [key: string]: string
}

export interface TemplatesConfig {
  allowed: string[]
}

export interface SectorFullConfig {
  code: string
  name: string
  description?: string
  branding: BrandingConfig
  fields: FieldsConfig
  features: FeaturesConfig
  defaults: DefaultsConfig
  endpoints: EndpointsConfig
  templates: TemplatesConfig
}

export interface SectorFullConfigResponse {
  ok: boolean
  code: string
  name: string
  description?: string
  sector: SectorFullConfig
}

interface UseSectorFullConfigState {
  config: SectorFullConfig | null
  loading: boolean
  error: string | null
}

// ============================================================================
// HOOK PRINCIPAL
// ============================================================================

const configCache = new Map<string, { config: SectorFullConfig; timestamp: number }>()
const CACHE_TTL = 5 * 60 * 1000 // 5 minutos

export function useCompanySectorFullConfig(
  sectorCode: string | null | undefined
): UseSectorFullConfigState {
  const [state, setState] = useState<UseSectorFullConfigState>({
    config: null,
    loading: false,
    error: null,
  })

  const loadConfig = useCallback(async () => {
    if (!sectorCode) {
      setState({ config: null, loading: false, error: null })
      return
    }

    // Verificar cache y validez (TTL)
    if (configCache.has(sectorCode)) {
      const cached = configCache.get(sectorCode)!
      if (Date.now() - cached.timestamp < CACHE_TTL) {
        setState({
          config: cached.config,
          loading: false,
          error: null,
        })
        return
      } else {
        // Cache expirado
        configCache.delete(sectorCode)
      }
    }

    setState({ config: null, loading: true, error: null })

    try {
      const encodedCode = encodeURIComponent(sectorCode.toLowerCase())
      const response = await tenantApi.get<SectorFullConfigResponse>(
        `/api/v1/sectors/${encodedCode}/full-config`
      )

      const config = response.data.sector

      // Guardar en cache con timestamp
      configCache.set(sectorCode, {
        config,
        timestamp: Date.now(),
      })

      setState({
        config,
        loading: false,
        error: null,
      })
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail ||
        err.message ||
        `Error cargando configuración del sector '${sectorCode}'`

      console.error('[useCompanySectorFullConfig]', {
        sectorCode,
        error: errorMessage,
        status: err.response?.status,
      })

      setState({
        config: null,
        loading: false,
        error: errorMessage,
      })
    }
  }, [sectorCode])

  useEffect(() => {
    loadConfig()
  }, [loadConfig])

  return state
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

export function getSectorIcon(config: SectorFullConfig | null): string {
  return config?.branding?.icon || '🏢'
}

export function getSectorColor(config: SectorFullConfig | null): string {
  return config?.branding?.color_primario || '#6366f1'
}

export function getSectorDisplayName(config: SectorFullConfig | null): string {
  return config?.branding?.displayName || 'General'
}

export function getSectorFeatures(config: SectorFullConfig | null): FeaturesConfig {
  return (
    config?.features || {
      expiry_tracking: false,
      lot_tracking: false,
      serial_tracking: false,
      batch_tracking: false,
      weight_tracking: false,
    }
  )
}

export function getSectorFieldAliases(
  config: SectorFullConfig | null,
  module: string
): Record<string, string[]> {
  return config?.fields?.[module]?.aliases || {}
}

export function getSectorFieldValidations(
  config: SectorFullConfig | null,
  module: string
): Record<string, string> {
  return config?.fields?.[module]?.validations || {}
}

export function getFieldPlaceholder(
  config: SectorFullConfig | null,
  field: string
): string {
  // Buscar en todos los módulos
  if (!config?.fields) return ''

  for (const module of Object.keys(config.fields)) {
    const placeholder = config.fields[module]?.placeholders?.[field]
    if (placeholder) return placeholder
  }

  return ''
}

export function getSectorDefaults(config: SectorFullConfig | null): DefaultsConfig {
  return (
    config?.defaults || {
      categories: [],
      tax_rate: null,
      currency: null,
      locale: 'es',
      timezone: 'Europe/Madrid',
      price_includes_tax: true,
    }
  )
}

export function getSectorEndpoints(config: SectorFullConfig | null): EndpointsConfig {
  return (
    config?.endpoints || {
      imports: '/api/v1/imports/batches',
      products: '/api/v1/tenant/products',
      customers: '/api/v1/tenant/customers',
    }
  )
}

export function getSectorUnits(config: SectorFullConfig | null): SectorUnit[] {
  return (
    config?.branding?.units || [
      { code: 'unit', label: 'Unidad' },
      { code: 'kg', label: 'Kilogramo' },
      { code: 'l', label: 'Litro' },
    ]
  )
}

// ============================================================================
// CACHE MANAGEMENT
// ============================================================================

export function clearSectorFullConfigCache() {
  configCache.clear()
}

export function clearSectorFullConfigCacheForCode(sectorCode: string) {
  configCache.delete(sectorCode)
}

export function getSectorFullConfigCacheSize(): number {
  return configCache.size
}
