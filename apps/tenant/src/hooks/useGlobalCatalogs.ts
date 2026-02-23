import { useEffect, useState } from 'react'
import api from '../shared/api/client'

type CatalogItem = { id: number | string; code: string; name: string; [k: string]: any }

function useCatalog(endpoint: string) {
  const [items, setItems] = useState<CatalogItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    api.get(endpoint)
      .then(({ data }) => { if (mounted) setItems(data || []) })
      .catch(() => {})
      .finally(() => { if (mounted) setLoading(false) })
    return () => { mounted = false }
  }, [endpoint])

  return { items, loading }
}

export function useCountries() { return useCatalog('/api/v1/tenant/catalogs/countries') }
export function useTaxTypes(countryCode?: string) {
  const qs = countryCode ? `?country_code=${countryCode}` : ''
  return useCatalog(`/api/v1/tenant/catalogs/tax-types${qs}`)
}
export function useUnits() { return useCatalog('/api/v1/tenant/catalogs/units') }
export function useDocTypes() { return useCatalog('/api/v1/tenant/catalogs/doc-types') }
export function useExpenseCategories() { return useCatalog('/api/v1/tenant/catalogs/expense-categories') }
export function usePaymentMethods() { return useCatalog('/api/v1/tenant/catalogs/payment-methods') }
