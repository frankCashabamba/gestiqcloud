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
  inventory?: {
    reorder_point_default?: number
    allow_negative?: boolean
    allow_negative_stock?: boolean
    track_lots?: boolean
    track_expiry?: boolean
  }
  pos_config?: {
    allow_negative?: boolean
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
    // New endpoint (consolidated in backend)
    // Fallback a ruta antigua si es necesario
    let data: TenantSettings
    try {
      const response = await tenantApi.get<TenantSettings>('/api/v1/company/settings')
      data = response.data
    } catch {
      // Fallbacks legacy si el endpoint nuevo no existe
      try {
        console.warn('Primary endpoint not available, trying legacy endpoint')
        const response = await tenantApi.get<TenantSettings>('/api/v1/settings/tenant')
        data = response.data
      } catch {
        const response = await tenantApi.get<TenantSettings>('/api/v1/tenants/self/settings')
        data = response.data
      }
    }

    cachedSettings = data
    return data
  } catch (error) {
    console.error('Error loading tenant settings:', error)
    // No devolver datos de otro tenant ni hardcodear: responde estructura vacía y reintenta en siguientes llamadas
    return {
      currency: '',
      locale: '',
      timezone: '',
      settings: {},
      inventory: {},
      pos_config: {},
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
export function getDefaultTaxRate(settings?: TenantSettings, fallback: number = 0.15): number {
  // Usa ?? para respetar ceros explícitos y evitar caer al 0.15 por falsy
  const posRate = settings?.pos_config?.tax?.default_rate
  const legacyRate = settings?.settings?.iva_tasa_defecto
  return posRate ?? legacyRate ?? fallback
}

export function getDefaultReorderPoint(settings?: TenantSettings): number {
  const inv =
    settings?.inventory?.reorder_point_default ??
    (settings?.settings as any)?.inventory?.reorder_point_default
  const num = Number(inv)
  return Number.isFinite(num) ? num : 0
}
