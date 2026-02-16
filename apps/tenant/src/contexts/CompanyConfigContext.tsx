/**
 * CompanyConfigContext
 *
 * Provider global que carga y distribuye la configuración de la empresa
 * según el sector seleccionado (panadería, taller, retail, etc.)
 *
 * Incluye:
 * - Configuración básica de la empresa
 * - Sector completo con features, fields, defaults, endpoints
 * - Features para condicionales (reemplaza is_panaderia, etc.)
 *
 * Uso:
 * ```tsx
 * const { config, features, sector, sectorConfig } = useCompanyConfig()
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
  useRef,
  useState,
  ReactNode,
} from 'react'
import { apiFetch } from '../lib/http'
import { useCompanySectorFullConfig as useCompanySectorFullConfigHook, SectorFullConfig, FeaturesConfig as SectorFeaturesConfig } from '../hooks/useCompanySectorFullConfig'
import i18n, { normalizeLang } from '../i18n'
import { useAuth } from '../auth/AuthContext'

interface CompanyInfo {
  id: string
  name: string
  color_primario: string
  plantilla_inicio: string
  currency: string
  country: string
  config_json: any
}

interface CompanySettings {
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

interface CompanyConfigData {
  company: CompanyInfo
  settings: CompanySettings
  categories: Category[]
  enabled_modules: string[]
  features: Features
  sector: Sector
}

interface CompanyConfigContextValue {
  config: CompanyConfigData | null
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

const CompanyConfigContext = createContext<CompanyConfigContextValue | undefined>(undefined)

export function CompanyConfigProvider({ children }: { children: ReactNode }) {
  const { token, loading: authLoading } = useAuth()
  const [config, setConfig] = useState<CompanyConfigData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const loadSeqRef = useRef(0)

  // NUEVO (Fase 2): Cargar configuración completa del sector
  const { config: sectorConfig, loading: sectorConfigLoading } = useCompanySectorFullConfigHook(
    config?.sector?.plantilla || null
  )

  const loadConfig = useCallback(async () => {
    // Only fetch protected company config after auth bootstrap is finished.
    if (authLoading) return
    if (!token) {
      setConfig(null)
      setError(null)
      setLoading(false)
      return
    }

    const loadSeq = ++loadSeqRef.current
    try {
      setLoading(true)
      setError(null)

      const response = await apiFetch('/api/v1/company/settings/config') as any
      if (loadSeq !== loadSeqRef.current) return
      const mapped: CompanyConfigData = {
        ...response,
        company: response?.tenant,
      }

      const lang = normalizeLang(mapped?.settings?.locale)
      if (i18n.resolvedLanguage !== lang) {
        try {
          await i18n.changeLanguage(lang)
        } catch {}
      }
      try {
        localStorage.setItem('i18nextLng', lang)
      } catch {}
      setConfig(mapped)
    } catch (err: any) {
      if (loadSeq !== loadSeqRef.current) return
      if (err?.status === 401) {
        setConfig(null)
        setError(null)
        return
      }
      console.error('Error loading company config:', err)
      setError(err.message || 'Error cargando configuracion de la empresa')
    } finally {
      if (loadSeq === loadSeqRef.current) {
        setLoading(false)
      }
    }
  }, [authLoading, token])

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

  const value: CompanyConfigContextValue = {
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
    <CompanyConfigContext.Provider value={value}>
      {children}
    </CompanyConfigContext.Provider>
  )
}

export function useCompanyConfig(): CompanyConfigContextValue {
  const context = useContext(CompanyConfigContext)
  if (!context) {
    throw new Error('useCompanyConfig must be used within CompanyConfigProvider')
  }
  return context
}

// Hook simplificado para solo features
export function useCompanyFeatures(): Features {
  const { features } = useCompanyConfig()
  return features
}

// Hook simplificado para solo sector
export function useCompanySector(): Sector {
  const { sector } = useCompanyConfig()
  return sector
}

// ============================================================================
// NUEVOS HOOKS DERIVADOS (Fase 2)
// ============================================================================

/**
 * Hook para acceder a la configuración completa del sector
 * Reemplaza hardcoding de is_panaderia, is_taller, etc.
 */
export function useCompanySectorFullConfig(): SectorFullConfig | null {
  const { sectorConfig } = useCompanyConfig()
  return sectorConfig
}

/**
 * Hook para acceder a features desde sectorConfig
 * Uso: if (useSectorFeaturesFromConfig().expiry_tracking) { ... }
 */
export function useSectorFeaturesFromConfig(): SectorFeaturesConfig {
  const sectorConfig = useCompanySectorFullConfig()
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
  const sectorConfig = useCompanySectorFullConfig()
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
  const sectorConfig = useCompanySectorFullConfig()
  return sectorConfig?.defaults || {}
}

/**
 * Hook para acceder a endpoints configurables del sector
 */
export function useSectorEndpoints() {
  const sectorConfig = useCompanySectorFullConfig()
  return sectorConfig?.endpoints || {}
}

export default CompanyConfigContext
