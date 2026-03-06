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

export type ProductCreatePayload = {
  name: string
  price: number
  stock: number
  unit: string
  category?: string
  sku?: string
  description?: string
  tax_rate?: number
  cost_price?: number
  active?: boolean
}

export async function listProducts(params?: { q?: string; limit?: number }) {
  // Use tenant-scoped endpoint; compatible with both array and {items}
  const { data } = await api.get<Product[] | { items?: Product[] }>('/api/v1/tenant/products', { params })
  if (Array.isArray(data)) return data
  const items = (data as any)?.items
  return Array.isArray(items) ? items : []
}

export async function createProduct(payload: ProductCreatePayload) {
  const { data } = await api.post<Product>('/api/v1/tenant/products', payload)
  return data
}
