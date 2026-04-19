import tenantApi from '../shared/api/client'
import type { BulkPricingItem } from '../modules/pos/bakeryShortcuts'

export type PosTheme = 'corporate-dark' | 'soft-dark' | 'light'

export interface CompanySettings {
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
    theme?: PosTheme | string
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
    invoice?: {
      minimum_amount?: number
      require_buyer_data?: boolean
      auto_create_wholesale?: boolean
    }
    bulk_pricing_items?: BulkPricingItem[]
  }
  invoice_config?: {
    serie_factura?: string
    autorizacion_sri?: string
  }
}

let cachedSettings: CompanySettings | null = null

export async function getCompanySettings(options?: { force?: boolean }): Promise<CompanySettings> {
  if (cachedSettings && !options?.force) {
    return cachedSettings
  }

  try {
    const response = await tenantApi.get<CompanySettings>('/api/v1/company/settings')
    cachedSettings = response.data
    return response.data
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

export function clearCompanySettingsCache() {
  cachedSettings = null
}

export async function updateCompanySettings(payload: Partial<CompanySettings>) {
  await tenantApi.put('/api/v1/company/settings', payload)
  clearCompanySettingsCache()
}

export async function savePosTheme(theme: PosTheme, currentSettings?: CompanySettings | null) {
  const base = currentSettings || (await getCompanySettings())
  const currentPosConfig = (base?.pos_config || {}) as Record<string, any>
  await updateCompanySettings({
    pos_config: {
      ...currentPosConfig,
      theme,
    },
  } as Partial<CompanySettings>)
}

// Helper para formatear moneda
export function formatCurrency(amount: number, settings?: CompanySettings): string {
  const rawCurrency = (settings?.currency || '').trim().toUpperCase()
  const isValidCurrency = /^[A-Z]{3}$/.test(rawCurrency)
  const rawLocale = (settings?.locale || '').trim()
  // Normaliza locale: convierte es_EC -> es-EC
  const locale = rawLocale ? rawLocale.replace(/_/g, '-') : undefined

  const plainOptions: Intl.NumberFormatOptions = {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }

  if (!isValidCurrency) {
    // Sin moneda válida, formatea como número plano con locale normalizado
    try {
      return new Intl.NumberFormat(locale, plainOptions).format(amount)
    } catch {
      try {
        return new Intl.NumberFormat('es-EC', plainOptions).format(amount)
      } catch {
        return new Intl.NumberFormat(undefined, plainOptions).format(amount)
      }
    }
  }

  const currencyOptions: Intl.NumberFormatOptions = {
    style: 'currency',
    currency: rawCurrency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }

  try {
    return new Intl.NumberFormat(locale, currencyOptions).format(amount)
  } catch (error) {
    // Fallbacks en cascada si el locale es inválido o la combinación locale/moneda falla
    console.warn(`Error formateando moneda con locale "${rawLocale}" y currency "${rawCurrency}"`, error)
    try {
      return new Intl.NumberFormat('es-EC', currencyOptions).format(amount)
    } catch {
      try {
        return new Intl.NumberFormat(undefined, currencyOptions).format(amount)
      } catch {
        return new Intl.NumberFormat(locale, plainOptions).format(amount)
      }
    }
  }
}

// Helper para obtener símbolo de moneda
export function getCurrencySymbol(settings?: CompanySettings): string {
  const currency = (settings?.currency || '').trim().toUpperCase()
  if (!currency) return ''

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
export function getDefaultTaxRate(settings?: CompanySettings, fallback: number = 0): number {
  // Usa ?? para respetar ceros explícitos y evitar caer al 0.15 por falsy
  const posRate = settings?.pos_config?.tax?.default_rate
  const legacyRate = settings?.settings?.iva_tasa_defecto
  return posRate ?? legacyRate ?? fallback
}

export function getDefaultReorderPoint(settings?: CompanySettings): number {
  const inv =
    settings?.inventory?.reorder_point_default ??
    (settings?.settings as any)?.inventory?.reorder_point_default
  const num = Number(inv)
  return Number.isFinite(num) ? num : 0
}

// Helper para obtener configuración de facturación automática
export function getInvoiceConfig(settings?: CompanySettings) {
  return {
    minimumAmount: settings?.pos_config?.invoice?.minimum_amount ?? 0,
    requireBuyerData: settings?.pos_config?.invoice?.require_buyer_data ?? false,
    autoCreateWholesale: settings?.pos_config?.invoice?.auto_create_wholesale ?? false,
  }
}

/**
 * Determina si se debe requerir factura basado en:
 * 1. Monto superior al mínimo configurado
 * 2. Cliente mayorista (opcional)
 */
export function shouldCreateInvoice(
  totalAmount: number,
  isWholesale: boolean,
  settings?: CompanySettings
): boolean {
  const config = getInvoiceConfig(settings)

  // Si es mayorista y está configurado auto-crear para mayoristas
  if (isWholesale && config.autoCreateWholesale) {
    return true
  }

  // Si supera el mínimo configurado
  if (config.minimumAmount > 0 && totalAmount >= config.minimumAmount) {
    return true
  }

  return false
}
