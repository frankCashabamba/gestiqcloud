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
  const items = (data as { items?: Product[] }).items
  return Array.isArray(items) ? items : []
}

export async function listRawMaterials(params?: { q?: string; limit?: number }) {
  const { data } = await api.get<Product[] | { items?: Product[] }>('/api/v1/tenant/products/raw-materials', {
    params,
  })
  if (Array.isArray(data)) return data.map(normalizeProduct)
  const items = (data as { items?: Product[] }).items
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

// === VARIANTES DE PRODUCTO ===

const VARIANTS_BASE = '/api/v1/tenant/products/variants'

export interface ProductAttribute {
  id: string
  name: string
  values: string[]
}

export interface ProductVariant {
  id: string
  product_id: string
  sku: string | null
  attributes: Record<string, string>
  price: number | null
  cost: number | null
  barcode: string | null
  is_active: boolean
}

export interface ProductAttributeCreatePayload {
  product_id: string
  name: string
  values: string[]
}

export interface ProductVariantCreatePayload {
  product_id: string
  sku: string | null
  attributes: Record<string, string>
  price: number | null
  cost: number | null
  barcode: string | null
}

export type ProductVariantUpdatePayload = Partial<{
  sku: string | null
  attributes: Record<string, string>
  price: number | null
  cost: number | null
  barcode: string | null
  is_active: boolean
}>

export async function listProductVariants(productId: string): Promise<ProductVariant[]> {
  const { data } = await api.get<ProductVariant[]>(`${VARIANTS_BASE}/${productId}`)
  return data
}

export async function listProductAttributes(productId: string): Promise<ProductAttribute[]> {
  // Scoped to this product so attributes from other tenants are never exposed
  const { data } = await api.get<ProductAttribute[]>(
    `${VARIANTS_BASE}/attributes?product_id=${encodeURIComponent(productId)}`,
  )
  return data
}

export async function createProductAttribute(
  payload: ProductAttributeCreatePayload,
): Promise<ProductAttribute> {
  const { data } = await api.post<ProductAttribute>(`${VARIANTS_BASE}/attributes`, payload)
  return data
}

export async function deleteProductAttribute(attributeId: string): Promise<void> {
  await api.delete(`${VARIANTS_BASE}/attributes/${attributeId}`)
}

export async function createProductVariant(
  payload: ProductVariantCreatePayload,
): Promise<ProductVariant> {
  const { data } = await api.post<ProductVariant>(VARIANTS_BASE, payload)
  return data
}

export async function updateProductVariant(
  variantId: string,
  payload: ProductVariantUpdatePayload,
): Promise<ProductVariant> {
  const { data } = await api.put<ProductVariant>(`${VARIANTS_BASE}/${variantId}`, payload)
  return data
}

export async function deleteProductVariant(variantId: string): Promise<void> {
  await api.delete(`${VARIANTS_BASE}/${variantId}`)
}
