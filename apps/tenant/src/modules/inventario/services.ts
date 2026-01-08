// apps/tenant/src/modules/inventario/services.ts
import { apiFetch } from '../../lib/http'

// Base de API para inventario (coincide con rutas backend)
const INVENTORY_BASE = '/api/v1/tenant/inventory'

// Tipos básicos usados por las vistas
export type Warehouse = {
  id: string | number
  code: string
  name: string
  is_active: boolean
}

export type StockItem = {
  id: string | number
  product_id: string | number
  warehouse_id: string | number
  qty: number
  location?: string | null
  lot?: string | null
  expires_at?: string | null
  product?: {
    id?: string | number
    sku?: string
    name?: string
    price?: number
    product_metadata?: {
      reorder_point?: number
      max_stock?: number
    }
  }
  warehouse?: Warehouse
}

// Helpers de mapeo tolerantes a estructuras variadas del backend
function mapWarehouse(w: any): Warehouse {
  return {
    id: w.id ?? w.warehouse_id ?? w.uuid ?? String(Math.random()),
    code: w.code ?? w.codigo ?? w.slug ?? '',
    name: w.name ?? w.nombre ?? '',
    is_active: Boolean(w.is_active ?? w.activo ?? true),
  }
}

function mapStockItem(x: any): StockItem {
  const product = x.product ?? x.producto ?? {}
  const wh = x.warehouse ?? x.almacen ?? x.w ?? {}
  return {
    id: x.id ?? x.item_id ?? `${product.id ?? ''}-${x.warehouse_id ?? ''}`,
    product_id: x.product_id ?? product.id ?? x.pid,
    warehouse_id: x.warehouse_id ?? wh.id ?? x.wid,
    qty: Number(x.qty ?? x.quantity ?? x.cantidad ?? 0),
    location: x.location ?? x.ubicacion ?? null,
    lot: x.lot ?? x.lote ?? null,
    expires_at: x.expires_at ?? x.caducidad ?? null,
    product: {
      id: product.id,
      sku: product.sku ?? product.codigo ?? product.code,
      name: product.name ?? product.nombre,
      price: Number(product.price ?? product.precio ?? 0),
      product_metadata: product.product_metadata ?? {
        reorder_point: product.stock_minimo ?? undefined,
        max_stock: product.stock_maximo ?? undefined,
      },
    },
    warehouse: Object.keys(wh).length ? mapWarehouse(wh) : undefined,
  }
}

// Warehouses API
export async function listWarehouses(): Promise<Warehouse[]> {
  const data = await apiFetch<any[]>(`${INVENTORY_BASE}/warehouses`)
  return (data || []).map(mapWarehouse)
}

export async function createWarehouse(data: { code: string; name: string; is_active?: boolean }): Promise<Warehouse> {
  const res = await apiFetch<any>(`${INVENTORY_BASE}/warehouses`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return mapWarehouse(res)
}

export async function updateWarehouse(id: string | number, patch: Partial<Pick<Warehouse, 'code' | 'name' | 'is_active'>>): Promise<Warehouse> {
  const res = await apiFetch<any>(`${INVENTORY_BASE}/warehouses/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  })
  return mapWarehouse(res)
}

// Stock Items API
export async function listStockItems(params?: { warehouse_id?: string | number; product_id?: string | number }): Promise<StockItem[]> {
  const q = new URLSearchParams()
  if (params?.warehouse_id) q.append('warehouse_id', String(params.warehouse_id))
  if (params?.product_id) q.append('product_id', String(params.product_id))
  const url = q.toString() ? `${INVENTORY_BASE}/stock?${q}` : `${INVENTORY_BASE}/stock`
  const data = await apiFetch<any>(url)
  const items = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : []
  return (items || []).map(mapStockItem)
}

// Movimientos / Ajustes
export async function createStockMove(data: {
  product_id: string | number
  warehouse_id: string | number
  qty: number
  kind: 'purchase' | 'sale' | 'adjustment' | 'transfer' | 'production' | 'return' | 'loss'
  notes?: string
  lote?: string
  expires_at?: string
}): Promise<any> {
  return apiFetch(`${INVENTORY_BASE}/stock/adjust`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      warehouse_id: data.warehouse_id,
      product_id: data.product_id,
      delta: Number(data.qty),
      reason: data.notes || data.kind,
    }),
  })
}

export async function adjustStock(data: { warehouse_id: string | number; product_id: string | number; delta: number; reason?: string }): Promise<any> {
  // Implementado sobre createStockMove con kind=adjustment
  return createStockMove({
    product_id: data.product_id,
    warehouse_id: data.warehouse_id,
    qty: Number(data.delta),
    kind: 'adjustment',
    notes: data.reason,
  })
}


// Existing warehouse and stock services...

// Alert Configuration Types
export interface AlertConfig {
  id: string
  name: string
  is_active: boolean
  alert_type: string
  threshold_type: string
  threshold_value: number
  warehouse_ids: string[]
  category_ids: string[]
  product_ids: string[]
  notify_email: boolean
  email_recipients: string[]
  notify_whatsapp: boolean
  whatsapp_numbers: string[]
  notify_telegram: boolean
  telegram_chat_ids: string[]
  check_frequency_minutes: number
  cooldown_hours: number
  max_alerts_per_day: number
  last_checked_at?: string
  next_check_at?: string
  created_at: string
  updated_at: string
}

export interface AlertHistory {
  id: string
  alert_config_id: string
  product_id: string
  warehouse_id?: string
  alert_type: string
  threshold_value: number
  current_stock: number
  message: string
  channels_sent: string[]
  sent_at: string
}

// Alert Configuration API
export async function listAlertConfigs(): Promise<AlertConfig[]> {
  return apiFetch<AlertConfig[]>(`${INVENTORY_BASE}/alerts/configs`)
}

export async function createAlertConfig(config: Omit<AlertConfig, 'id' | 'created_at' | 'updated_at'>): Promise<AlertConfig> {
  return apiFetch<AlertConfig>(`${INVENTORY_BASE}/alerts/configs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
}

export async function updateAlertConfig(configId: string, config: Partial<AlertConfig>): Promise<AlertConfig> {
  return apiFetch<AlertConfig>(`${INVENTORY_BASE}/alerts/configs/${configId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
}

export async function deleteAlertConfig(configId: string): Promise<void> {
  await apiFetch(`${INVENTORY_BASE}/alerts/configs/${configId}`, {
    method: 'DELETE',
  })
}

export async function testAlertConfig(configId: string): Promise<{ status: string; channels_sent: string[]; errors?: string[] }> {
  return apiFetch(`${INVENTORY_BASE}/alerts/test/${configId}`, {
    method: 'POST',
  })
}

export async function checkAlerts(): Promise<{ status: string; alerts_sent: number; errors: string[] }> {
  return apiFetch(`${INVENTORY_BASE}/alerts/check`, {
    method: 'POST',
  })
}

export async function listAlertHistory(limit?: number, daysBack?: number): Promise<AlertHistory[]> {
  const params = new URLSearchParams()
  if (limit) params.append('limit', limit.toString())
  if (daysBack) params.append('days_back', daysBack.toString())

  const url = params.toString() ? `${INVENTORY_BASE}/alerts/history?${params.toString()}` : `${INVENTORY_BASE}/alerts/history`
  return apiFetch<AlertHistory[]>(url)
}
