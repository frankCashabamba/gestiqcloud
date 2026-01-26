// apps/tenant/src/hooks/useCurrency.ts
import { useEffect, useState } from 'react'
import { apiFetch } from '../lib/http'

type CompanyInfo = {
  base_currency?: string
  country_code?: string
}

type CompanySettings = {
  currency?: string
  settings?: {
    currency?: string
  }
}

const normalizeCurrency = (raw?: string): string => {
  const code = (raw || '').trim().toUpperCase()
  if (!code) return ''
  const aliases: Record<string, string> = { US: 'USD', USA: 'USD' }
  return aliases[code] || code
}

const extractSymbol = (currencyCode: string, locale?: string): string => {
  try {
    const parts = new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: currencyCode,
      currencyDisplay: 'narrowSymbol',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).formatToParts(0)
    const currencyPart = parts.find((p) => p.type === 'currency')
    return currencyPart?.value || currencyCode
  } catch {
    return currencyCode
  }
}

export function useCurrency() {
  const [currency, setCurrency] = useState<string>('')
  const [symbol, setSymbol] = useState<string>('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {

    ;(async () => {
      try {
        const tenant = await apiFetch<CompanyInfo>('/api/v1/me/tenant')
        let normalized = normalizeCurrency(tenant?.base_currency)

        if (!normalized) {
          const settings = await apiFetch<CompanySettings>('/api/v1/company/settings')
          normalized = normalizeCurrency(settings?.currency || settings?.settings?.currency)
        }

        const sym = normalized ? extractSymbol(normalized) : ''

        console.log('[useCurrency] Company currency:', tenant?.base_currency, 'Normalized:', normalized, 'Symbol:', sym)

        setCurrency(normalized)
        setSymbol(sym)
      } catch (e) {
        console.error('Error cargando moneda del tenant:', e)
        setCurrency('')
        setSymbol('')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const formatCurrency = (amount: number): string => {
    if (!currency) {
      return new Intl.NumberFormat(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(amount)
    }
    return new Intl.NumberFormat(undefined, {
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
