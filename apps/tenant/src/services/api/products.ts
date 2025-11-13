import api from '../../shared/api/client'

export type Product = {
  id: string
  code?: string
  name: string
  price: number
  cost_price?: number
  tax_rate: number
  image_url?: string
  category?: string
  uom?: string
  unit?: string
  weight_required?: boolean
}

export async function listProducts(params?: { q?: string; limit?: number }) {
  // Use tenant-scoped endpoint; compatible with both array and {items}
  const { data } = await api.get<Product[] | { items?: Product[] }>('/api/v1/tenant/products', { params })
  if (Array.isArray(data)) return data
  const items = (data as any)?.items
  return Array.isArray(items) ? items : []
}
