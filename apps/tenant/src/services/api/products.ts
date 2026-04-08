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

function normalizeProduct(raw: any): Product {
  return {
    id: String(raw?.id || ''),
    code: raw?.code,
    name: String(raw?.name || ''),
    price: Number(raw?.price || 0),
    cost_price: raw?.cost_price != null ? Number(raw.cost_price) : undefined,
    tax_rate: Number(raw?.tax_rate || 0),
    image_url: raw?.image_url,
    category: raw?.category,
    uom: raw?.uom,
    unit: raw?.unit,
    weight_required: Boolean(raw?.weight_required),
  }
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
  is_raw_material?: boolean
}

export async function listProducts(params?: { q?: string; limit?: number }) {
  // Use tenant-scoped endpoint; compatible with both array and {items}
  const { data } = await api.get<Product[] | { items?: Product[] }>('/api/v1/tenant/products', { params })
  if (Array.isArray(data)) return data
  const items = (data as any)?.items
  return Array.isArray(items) ? items : []
}

export async function listRawMaterials(params?: { q?: string; limit?: number }) {
  const { data } = await api.get<Product[] | { items?: Product[] }>('/api/v1/tenant/products/raw-materials', {
    params,
  })
  if (Array.isArray(data)) return data.map(normalizeProduct)
  const items = (data as any)?.items
  return Array.isArray(items) ? items.map(normalizeProduct) : []
}

export async function createProduct(payload: ProductCreatePayload) {
  const { data } = await api.post<Product>('/api/v1/tenant/products', payload)
  return data
}

export async function updateProduct(id: string, payload: Partial<ProductCreatePayload & { name: string }>) {
  const { data } = await api.put<Product>(`/api/v1/tenant/products/${id}`, payload)
  return data
}
