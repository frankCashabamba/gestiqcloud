import tenantApi from '../shared/api/client'

export interface TenantSettings {
  currency: string
  locale: string
  timezone: string
  settings: {
    iva_tasa_defecto?: number
    empresa_nombre?: string
    pais?: string
  }
  pos_config?: {
    tax?: {
      price_includes_tax?: boolean
      default_rate?: number
    }
    return_window_days?: number
    store_credit?: {
      single_use?: boolean
      expiry_months?: number
    }
    receipt?: {
      width_mm?: number
      print_mode?: string
    }
  }
  invoice_config?: {
    serie_factura?: string
    autorizacion_sri?: string
  }
}

let cachedSettings: TenantSettings | null = null

export async function getTenantSettings(): Promise<TenantSettings> {
  if (cachedSettings) {
    return cachedSettings
  }

  try {
    const { data } = await tenantApi.get<TenantSettings>('/api/v1/settings/tenant')
    cachedSettings = data
    return data
  } catch (error) {
    console.error('Error loading tenant settings:', error)
    // Fallback a valores por defecto
    return {
      currency: 'USD',
      locale: 'es-EC',
      timezone: 'America/Guayaquil',
      settings: {
        iva_tasa_defecto: 15,
        empresa_nombre: 'Panadería Kusi',
        pais: 'EC'
      },
      pos_config: {
        tax: {
          price_includes_tax: true,
          default_rate: 0.15
        },
        return_window_days: 15,
        store_credit: {
          single_use: true,
          expiry_months: 12
        },
        receipt: {
          width_mm: 58,
          print_mode: 'system'
        }
      }
    }
  }
}

export function clearSettingsCache() {
  cachedSettings = null
}

// Helper para formatear moneda
export function formatCurrency(amount: number, settings?: TenantSettings): string {
  const currency = settings?.currency || 'USD'
  const locale = settings?.locale || 'es-EC'
  
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount)
}

// Helper para obtener símbolo de moneda
export function getCurrencySymbol(settings?: TenantSettings): string {
  const currency = settings?.currency || 'USD'
  
  const symbols: Record<string, string> = {
    'USD': '$',
    'EUR': '€',
    'COP': '$',
    'PEN': 'S/',
    'MXN': '$'
  }
  
  return symbols[currency] || currency
}

// Helper para obtener tasa de IVA
export function getDefaultTaxRate(settings?: TenantSettings): number {
  return settings?.settings?.iva_tasa_defecto || settings?.pos_config?.tax?.default_rate || 0.15
}
