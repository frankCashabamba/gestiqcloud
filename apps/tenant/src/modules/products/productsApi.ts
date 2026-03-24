// apps/tenant/src/modules/products/productsApi.ts
// Centralized API client for products and categories
import { apiFetch } from '../../lib/http'
import { queueDeletion, storeEntity } from '../../lib/offlineStore'
import { createOfflineTempId, isNetworkIssue, stripOfflineMeta } from '../../lib/offlineHttp'
import { IMPORTS } from '@endpoints/imports'

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
    bulkGenerateSkus: '/api/v1/tenant/products/bulk/generate-skus',
    similarDuplicates: '/api/v1/tenant/products/duplicates/similar',
    mergeDuplicates: '/api/v1/tenant/products/duplicates/merge',
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
  price: number
  cost_price?: number | null
  tax_rate?: number | null
  category?: string | null
  category_id?: string | null
  active: boolean
  stock: number
  unit: string
  is_raw_material?: boolean
  suggested_price?: number | null
  use_suggested_price?: boolean
  product_metadata?: Record<string, any> | null
  import_aliases?: Array<{ name: string; factor: number; unit?: string }> | null
  created_at: string
  updated_at?: string
}

export type Categoria = {
  id: string
  name: string
  description?: string | null
  parent_id?: string | null
}

export type SimilarProductCandidate = {
  id: string
  name: string
  sku?: string | null
  price: number
  stock: number
  refs: number
}

export type SimilarProductGroup = {
  winner: SimilarProductCandidate
  candidates: SimilarProductCandidate[]
}

// ============================================================================
// PRODUCTS
// ============================================================================

export async function listProductos(hideOutOfStock: boolean = false): Promise<Producto[]> {
  const params = new URLSearchParams()
  if (hideOutOfStock) {
    params.append('active', 'true')
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
    description: p.description ?? null,
    price: Number(p.price ?? 0) || 0,
    cost_price: p.cost_price ?? null,
    tax_rate: p.tax_rate ?? null,
    category: typeof p.category === 'string' ? p.category : (p.category?.name ?? null),
    category_id: p.category_id ?? null,
    active: Boolean(p.active ?? true),
    stock: Number(p.stock ?? 0) || 0,
    unit: p.unit || 'unit',
    is_raw_material: Boolean(p.is_raw_material ?? false),
    suggested_price: p.suggested_price ?? null,
    use_suggested_price: Boolean(p.use_suggested_price ?? false),
    product_metadata: p.product_metadata ?? null,
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

function buildOfflineFallback(id: string, payload: any, isUpdate = false): Producto {
  return {
    id,
    tenant_id: String(payload.tenant_id || ''),
    sku: payload.sku ?? null,
    name: String(payload.name || ''),
    description: payload.description ?? null,
    price: Number(payload.price ?? 0) || 0,
    active: Boolean(payload.active ?? true),
    stock: Number(payload.stock ?? 0) || 0,
    unit: String(payload.unit || 'unit'),
    is_raw_material: Boolean(payload.is_raw_material ?? false),
    created_at: new Date().toISOString(),
    ...(isUpdate ? { updated_at: new Date().toISOString() } : {}),
  }
}

export async function createProducto(data: Partial<Producto>): Promise<Producto> {
  const cleanPayload = stripOfflineMeta(data as any)
  try {
    const created = await apiFetch<Producto | { queued: boolean }>(ENDPOINTS.products.create, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Offline-Managed': '1' },
      body: JSON.stringify(cleanPayload),
    })

    if ((created as any)?.queued === true) {
      const tempId = createOfflineTempId('product')
      await storeEntity('product', tempId, { ...cleanPayload, _op: 'create' }, 'pending')
      return buildOfflineFallback(tempId, cleanPayload)
    }

    return created as Producto
  } catch (error) {
    if (isNetworkIssue(error)) {
      const tempId = createOfflineTempId('product')
      await storeEntity('product', tempId, { ...cleanPayload, _op: 'create' }, 'pending')
      return buildOfflineFallback(tempId, cleanPayload)
    }
    throw error
  }
}

export async function updateProducto(id: string, data: Partial<Producto>): Promise<Producto> {
  const cleanPayload = stripOfflineMeta(data as any)
  try {
    const updated = await apiFetch<Producto | { queued: boolean }>(ENDPOINTS.products.update(id), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'X-Offline-Managed': '1' },
      body: JSON.stringify(cleanPayload),
    })

    if ((updated as any)?.queued === true) {
      await storeEntity('product', String(id), { ...cleanPayload, _op: 'update' }, 'pending')
      return buildOfflineFallback(String(id), cleanPayload, true)
    }

    return updated as Producto
  } catch (error) {
    if (isNetworkIssue(error)) {
      await storeEntity('product', String(id), { ...cleanPayload, _op: 'update' }, 'pending')
      return buildOfflineFallback(String(id), cleanPayload, true)
    }
    throw error
  }
}

export async function removeProducto(id: string): Promise<void> {
  try {
    const response = await apiFetch<any>(ENDPOINTS.products.delete(id), {
      method: 'DELETE',
      headers: { 'X-Offline-Managed': '1' },
    })
    if (response?.queued === true) {
      await queueDeletion('product', String(id))
    }
  } catch (error) {
    if (isNetworkIssue(error)) {
      await queueDeletion('product', String(id))
      return
    }
    throw error
  }
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

export async function bulkGenerateMissingSkus(): Promise<{ updated: number }> {
  return apiFetch<{ updated: number }>(ENDPOINTS.products.bulkGenerateSkus, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
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

export async function listSimilarProductDuplicates(
  threshold: number = 0.9,
  limit: number = 12,
): Promise<{ groups: SimilarProductGroup[]; total_groups: number }> {
  const params = new URLSearchParams({
    threshold: String(threshold),
    limit: String(limit),
  })
  return apiFetch<{ groups: SimilarProductGroup[]; total_groups: number }>(
    `${ENDPOINTS.products.similarDuplicates}?${params.toString()}`,
  )
}

export async function mergeSimilarProducts(
  winnerId: string,
  loserIds: string[],
): Promise<{ merged: number; winner_id: string; moved_refs: Record<string, number>; deleted_ids: string[] }> {
  return apiFetch(ENDPOINTS.products.mergeDuplicates, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ winner_id: winnerId, loser_ids: loserIds }),
  }) as any
}

export async function importProductosExcel(file: File): Promise<{ batch_id: string; items_count: number }> {
  const formData = new FormData()
  formData.append('file', file)
  const parsed = await apiFetch<{ headers: string[]; rows: Record<string, unknown>[] }>(IMPORTS.excel.parse, {
    method: 'POST',
    body: formData,
  })

  const batch = await apiFetch<{ id: string }>(IMPORTS.batches.base, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      source_type: 'products',
      origin: file.name || 'products-import',
    }),
  })

  const rows = Array.isArray(parsed?.rows) ? parsed.rows : []
  await apiFetch(IMPORTS.batches.ingest(batch.id), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rows }),
  })

  return { batch_id: batch.id, items_count: rows.length }
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
