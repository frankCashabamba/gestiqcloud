// apps/tenant/src/hooks/useCurrency.ts
import { useEffect, useState } from 'react'
import { apiFetch } from '../lib/http'

type TenantInfo = {
  base_currency?: string
  country_code?: string
}

const CURRENCY_SYMBOLS: Record<string, string> = {
  'EUR': '€',
  'USD': '$',
  'COP': '$',
  'PEN': 'S/',
  'MXN': '$'
}

const CURRENCY_LOCALE: Record<string, string> = {
  'EUR': 'es-ES',
  'USD': 'en-US',
  'COP': 'es-CO',
  'PEN': 'es-PE',
  'MXN': 'es-MX'
}

export function useCurrency() {
  const [currency, setCurrency] = useState<string>('USD')
  const [symbol, setSymbol] = useState<string>('$')
  const [loading, setLoading] = useState(true)

  useEffect(() => {

    ;(async () => {
      try {
        const tenant = await apiFetch<TenantInfo>('/api/v1/me/tenant')
        const curr = tenant?.base_currency || 'USD'
        const sym = CURRENCY_SYMBOLS[curr] || '$'

        console.log('[useCurrency] Tenant currency:', curr, 'Symbol:', sym)

        setCurrency(curr)
        setSymbol(sym)
      } catch (e) {
        console.error('Error cargando moneda del tenant:', e)
        setCurrency('USD')
        setSymbol('$')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const formatCurrency = (amount: number): string => {
    const locale = CURRENCY_LOCALE[currency] || 'en-US'
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount)
  }

  return {
    currency,
    symbol,
    loading,
    formatCurrency,
  }
}
