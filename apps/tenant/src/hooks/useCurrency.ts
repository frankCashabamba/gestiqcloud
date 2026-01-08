// apps/tenant/src/hooks/useCurrency.ts
import { useEffect, useState } from 'react'
import { apiFetch } from '../lib/http'

type CompanyInfo = {
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
        const tenant = await apiFetch<CompanyInfo>('/api/v1/me/tenant')
        const rawCurr = (tenant?.base_currency || 'USD').toUpperCase()
        const normalized = CURRENCY_LOCALE[rawCurr] ? rawCurr : 'USD'
        const sym = CURRENCY_SYMBOLS[normalized] || '$'

        console.log('[useCurrency] Company currency:', rawCurr, 'Normalized:', normalized, 'Symbol:', sym)

        setCurrency(normalized)
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
