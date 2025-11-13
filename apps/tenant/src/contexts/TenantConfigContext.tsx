/**
 * TenantConfigContext
 * 
 * Provider global que carga y distribuye la configuración del tenant
 * según el sector seleccionado (panadería, taller, retail, etc.)
 * 
 * Uso:
 * ```tsx
 * const { config, features, sector } = useTenantConfig()
 * 
 * {features.inventory_expiry_tracking && (
 *   <DateInput name="expires_at" label="Fecha de Caducidad" />
 * )}
 * ```
 */
import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { apiFetch } from '../lib/http'

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
  is_panaderia: boolean
  is_taller: boolean
  is_retail: boolean
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
}

const TenantConfigContext = createContext<TenantConfigContextValue | undefined>(undefined)

export function TenantConfigProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<TenantConfigData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadConfig = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const response = await apiFetch('/api/v1/settings/tenant-config') as TenantConfigData
      setConfig(response)
    } catch (err: any) {
      console.error('Error loading tenant config:', err)
      setError(err.message || 'Error cargando configuración del tenant')
      
      // Fallback: configuración por defecto
      setConfig({
        tenant: {
          id: '',
          name: 'Mi Empresa',
          color_primario: '#4f46e5',
          plantilla_inicio: 'default',
          currency: 'EUR',
          country: 'ES',
          config_json: {}
        },
        settings: {
          settings: {},
          pos_config: {},
          locale: 'es',
          timezone: 'Europe/Madrid',
          currency: 'EUR'
        },
        categories: [],
        enabled_modules: [],
        features: {
          inventory_expiry_tracking: false,
          inventory_lot_tracking: false,
          inventory_serial_tracking: false,
          inventory_auto_reorder: false,
          pos_enable_weights: false,
          pos_enable_batch_tracking: false,
          pos_receipt_width_mm: 58,
          pos_return_window_days: 15,
          price_includes_tax: true,
          tax_rate: 0.15
        },
        sector: {
          plantilla: 'default',
          is_panaderia: false,
          is_taller: false,
          is_retail: false
        }
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadConfig()
  }, [])

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
    isModuleEnabled
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

export default TenantConfigContext
