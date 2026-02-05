// apps/tenant/src/modules/products/productsApi.ts
// Centralized API client for products and categories
import { apiFetch } from '../../lib/http'

// ============================================================================
// ENDPOINTS
// ============================================================================

const ENDPOINTS = {
  products: {
    list: '/api/v1/tenant/products',
    get: (id: string) => `/api/v1/tenant/products/${id}`,
    create: '/api/v1/tenant/products',
    update: (id: string) => `/api/v1/tenant/products/${id}`,
    delete: (id: string) => `/api/v1/tenant/products/${id}`,
    search: (q: string) => `/api/v1/tenant/products/search?q=${encodeURIComponent(q)}`,
    purge: '/api/v1/tenant/products/purge',
    bulkActive: '/api/v1/tenant/products/bulk/active',
    bulkCategory: '/api/v1/tenant/products/bulk/category',
    importExcel: '/api/v1/imports/upload',
  },
  categories: {
    list: '/api/v1/tenant/products/product-categories',
    create: '/api/v1/tenant/products/product-categories',
    delete: (id: string) => `/api/v1/tenant/products/product-categories/${id}`,
  },
} as const

// ============================================================================
// TYPES
// ============================================================================

export type Producto = {
  id: string
  tenant_id: string
  sku: string | null
  name: string
  description?: string | null
  descripcion?: string | null
  price: number
  precio_compra?: number | null
  iva_tasa?: number | null
  categoria?: string | null
  active: boolean
  stock: number
  unit: string
  product_metadata?: Record<string, any> | null
  category_id?: string | null
  created_at: string
  updated_at?: string
}

export type Categoria = {
  id: string
  name: string
  description?: string | null
  parent_id?: string | null
}

// ============================================================================
// PRODUCTS
// ============================================================================

export async function listProductos(hideOutOfStock: boolean = false): Promise<Producto[]> {
  const params = new URLSearchParams()
  if (hideOutOfStock) {
    params.append('activo', 'true')
  }

  const url = params.toString()
    ? `${ENDPOINTS.products.list}?${params.toString()}`
    : ENDPOINTS.products.list

  const res = await apiFetch<any>(url)

  const toArray = (val: any) => (Array.isArray(val) ? val : Array.isArray(val?.items) ? val.items : [])

  const norm = (p: any): Producto => ({
    id: String(p.id),
    tenant_id: String(p.tenant_id || ''),
    sku: p.sku ?? null,
    name: p.name,
    description: p.description ?? p.descripcion ?? null,
    descripcion: undefined,
    price: Number(p.price ?? p.precio ?? 0) || 0,
    precio_compra: p.precio_compra ?? p.cost ?? p.cost_price ?? null,
    iva_tasa: p.iva_tasa ?? p.tax_rate ?? null,
    categoria: p.categoria ?? (typeof p.category === 'string' ? p.category : p.category?.name) ?? null,
    active: Boolean(p.active ?? p.activo ?? true),
    stock: Number(p.stock ?? 0) || 0,
    unit: p.unit || p.uom || 'unit',
    product_metadata: p.product_metadata ?? p.metadata ?? null,
    category_id: p.category_id ?? null,
    created_at: p.created_at || new Date().toISOString(),
    updated_at: p.updated_at || undefined,
  })

  let products = toArray(res).map(norm)

  if (hideOutOfStock) {
    products = products.filter((p) => p.stock > 0 && p.active)
  }

  return products
}

export async function getProducto(id: string): Promise<Producto> {
  return apiFetch<Producto>(ENDPOINTS.products.get(id))
}

export async function createProducto(data: Partial<Producto>): Promise<Producto> {
  return apiFetch<Producto>(ENDPOINTS.products.create, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateProducto(id: string, data: Partial<Producto>): Promise<Producto> {
  return apiFetch<Producto>(ENDPOINTS.products.update(id), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function removeProducto(id: string): Promise<void> {
  await apiFetch(ENDPOINTS.products.delete(id), { method: 'DELETE' })
}

export async function searchProductos(q: string): Promise<Producto[]> {
  const res = await apiFetch<any>(ENDPOINTS.products.search(q))
  if (Array.isArray(res)) return res as Producto[]
  if (res && Array.isArray(res.items)) return res.items as Producto[]
  return []
}

export async function bulkSetActive(ids: string[], active: boolean): Promise<{ updated: number }> {
  return apiFetch<{ updated: number }>(ENDPOINTS.products.bulkActive, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids, active }),
  })
}

export async function bulkAssignCategory(
  ids: string[],
  category_name: string,
): Promise<{ updated: number; category_created: boolean }> {
  return apiFetch<{ updated: number; category_created: boolean }>(ENDPOINTS.products.bulkCategory, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids, category_name }),
  })
}

export async function purgeProductos(): Promise<void> {
  await apiFetch(ENDPOINTS.products.purge, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirm: 'PURGE' }),
  })
}

export async function purgeProductosDryRun(): Promise<{ counts: Record<string, number> }> {
  return apiFetch(ENDPOINTS.products.purge, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dry_run: true, confirm: 'DRYRUN' }),
  }) as any
}

export async function purgeProductosConfirm(options?: {
  include_stock?: boolean
  include_categories?: boolean
  confirm?: string
}): Promise<{ deleted: Record<string, number> }> {
  const { include_stock = true, include_categories = true, confirm = 'PURGE' } = options || {}
  return apiFetch(ENDPOINTS.products.purge, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ include_stock, include_categories, confirm, dry_run: false }),
  }) as any
}

export async function importProductosExcel(file: File): Promise<{ batch_id: string; items_count: number }> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('entity_type', 'products')

  return apiFetch<{ batch_id: string; items_count: number }>(ENDPOINTS.products.importExcel, {
    method: 'POST',
    body: formData,
  })
}

// ============================================================================
// CATEGORIES
// ============================================================================

export async function listCategorias(): Promise<Categoria[]> {
  const data = await apiFetch<Categoria[]>(ENDPOINTS.categories.list)
  return Array.isArray(data) ? data : []
}

export async function createCategoria(name: string, description?: string): Promise<Categoria> {
  return apiFetch<Categoria>(ENDPOINTS.categories.create, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: name.trim(),
      description: description?.trim() || null,
    }),
  })
}

export async function deleteCategoria(id: string): Promise<void> {
  await apiFetch(ENDPOINTS.categories.delete(id), { method: 'DELETE' })
}
