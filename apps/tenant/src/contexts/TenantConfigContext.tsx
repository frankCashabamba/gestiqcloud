/**
 * TenantConfigContext
 *
 * Provider global que carga y distribuye la configuración del tenant
 * según el sector seleccionado (panadería, taller, retail, etc.)
 *
 * Incluye:
 * - Configuración básica del tenant
 * - Sector completo con features, fields, defaults, endpoints
 * - Features para condicionales (reemplaza is_panaderia, etc.)
 *
 * Uso:
 * ```tsx
 * const { config, features, sector, sectorConfig } = useTenantConfig()
 *
 * {features.inventory_expiry_tracking && (
 *   <DateInput name="expires_at" label="Fecha de Caducidad" />
 * )}
 *
 * {sectorConfig?.features?.expiry_tracking && (
 *   <ExpiryWarning />
 * )}
 * ```
 */
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from 'react'
import { apiFetch } from '../lib/http'
import { useSectorFullConfig as useSectorFullConfigHook, SectorFullConfig, FeaturesConfig as SectorFeaturesConfig } from '../hooks/useSectorFullConfig'

interface TenantInfo {
  id: string
  name: string
  color_primario: string
  plantilla_inicio: string
  currency: string
  country: string
  config_json: any
}

interface TenantSettings {
  settings: any
  pos_config: any
  locale: string
  timezone: string
  currency: string
}

interface Category {
  id: string
  name: string
  description?: string
}

interface Features {
  // Inventario
  inventory_expiry_tracking: boolean
  inventory_lot_tracking: boolean
  inventory_serial_tracking: boolean
  inventory_auto_reorder: boolean

  // POS
  pos_enable_weights: boolean
  pos_enable_batch_tracking: boolean
  pos_receipt_width_mm: number
  pos_return_window_days: number

  // General
  price_includes_tax: boolean
  tax_rate: number
}

interface Sector {
  plantilla: string
  /**
   * @deprecated FASE 7: Use features from config instead
   * Features are now loaded dynamically from database
   */
  is_panaderia?: boolean
  /**
   * @deprecated FASE 7: Use features from config instead
   */
  is_taller?: boolean
  /**
   * @deprecated FASE 7: Use features from config instead
   */
  is_retail?: boolean
  /**
   * Features dinámicas cargadas desde BD
   * Reemplaza is_panaderia, is_taller, is_retail
   */
  features?: Record<string, boolean>
}

interface TenantConfigData {
  tenant: TenantInfo
  settings: TenantSettings
  categories: Category[]
  enabled_modules: string[]
  features: Features
  sector: Sector
}

interface TenantConfigContextValue {
  config: TenantConfigData | null
  loading: boolean
  error: string | null
  reload: () => Promise<void>

  // Helpers de acceso rápido
  features: Features
  sector: Sector
  categories: Category[]
  isModuleEnabled: (moduleKey: string) => boolean

  // NUEVO: Configuración completa del sector (Fase 2)
  sectorConfig: SectorFullConfig | null
  sectorConfigLoading: boolean
}

const TenantConfigContext = createContext<TenantConfigContextValue | undefined>(undefined)

export function TenantConfigProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<TenantConfigData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // NUEVO (Fase 2): Cargar configuración completa del sector
  const { config: sectorConfig, loading: sectorConfigLoading } = useSectorFullConfigHook(
    config?.sector?.plantilla || null
  )

  const loadConfig = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await apiFetch('/api/v1/settings/tenant-config') as TenantConfigData
      setConfig(response)
    } catch (err: any) {
      console.error('Error loading tenant config:', err)
      setError(err.message || 'Error cargando configuración del tenant')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadConfig()
  }, [loadConfig])

  useEffect(() => {
    const handler = (event: StorageEvent) => {
      if (event.key === 'guc-sector-config-refresh') {
        loadConfig()
      }
    }

    window.addEventListener('storage', handler)
    return () => window.removeEventListener('storage', handler)
  }, [loadConfig])

  const isModuleEnabled = (moduleKey: string): boolean => {
    if (!config) return false
    return config.enabled_modules.includes(moduleKey)
  }

  const value: TenantConfigContextValue = {
    config,
    loading,
    error,
    reload: loadConfig,
    features: config?.features || {} as Features,
    sector: config?.sector || {} as Sector,
    categories: config?.categories || [],
    isModuleEnabled,
    // NUEVO (Fase 2)
    sectorConfig,
    sectorConfigLoading,
  }

  return (
    <TenantConfigContext.Provider value={value}>
      {children}
    </TenantConfigContext.Provider>
  )
}

export function useTenantConfig(): TenantConfigContextValue {
  const context = useContext(TenantConfigContext)
  if (!context) {
    throw new Error('useTenantConfig must be used within TenantConfigProvider')
  }
  return context
}

// Hook simplificado para solo features
export function useTenantFeatures(): Features {
  const { features } = useTenantConfig()
  return features
}

// Hook simplificado para solo sector
export function useTenantSector(): Sector {
  const { sector } = useTenantConfig()
  return sector
}

// ============================================================================
// NUEVOS HOOKS DERIVADOS (Fase 2)
// ============================================================================

/**
 * Hook para acceder a la configuración completa del sector
 * Reemplaza hardcoding de is_panaderia, is_taller, etc.
 */
export function useSectorFullConfig(): SectorFullConfig | null {
  const { sectorConfig } = useTenantConfig()
  return sectorConfig
}

/**
 * Hook para acceder a features desde sectorConfig
 * Uso: if (useSectorFeaturesFromConfig().expiry_tracking) { ... }
 */
export function useSectorFeaturesFromConfig(): SectorFeaturesConfig {
  const sectorConfig = useSectorFullConfig()
  return (
    sectorConfig?.features || {
      expiry_tracking: false,
      lot_tracking: false,
      serial_tracking: false,
      batch_tracking: false,
      weight_tracking: false,
    }
  )
}

/**
 * Hook para acceder a fields de un módulo específico
 * Uso: const productFields = useSectorFieldsForModule('products')
 */
export function useSectorFieldsForModule(module: string) {
  const sectorConfig = useSectorFullConfig()
  return sectorConfig?.fields?.[module] || {
    aliases: {},
    validations: {},
    placeholders: {},
  }
}

/**
 * Hook para acceder a defaults del sector
 */
export function useSectorDefaults() {
  const sectorConfig = useSectorFullConfig()
  return sectorConfig?.defaults || {}
}

/**
 * Hook para acceder a endpoints configurables del sector
 */
export function useSectorEndpoints() {
  const sectorConfig = useSectorFullConfig()
  return sectorConfig?.endpoints || {}
}

export default TenantConfigContext
