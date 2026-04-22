import tenantApi from '../../shared/api/client'
import { TENANT_PURCHASES } from '@shared/endpoints'
import { queueDeletion, storeEntity } from '../../lib/offlineStore'
import { createOfflineTempId, isNetworkIssue, isOfflineQueuedResponse, stripOfflineMeta } from '../../lib/offlineHttp'

export type PurchaseLine = {
  id?: number | string
  product_id: number | string
  quantity: number
  unit_price: number
  subtotal: number
}

export type Purchase = {
  id: number | string
  number?: string
  date: string
  delivery_date?: string
  supplier_id?: number | string
  supplier_name?: string
  subtotal: number
  taxes: number
  total: number
  status: 'draft' | 'sent' | 'received' | 'cancelled'
  lines?: PurchaseLine[]
  notes?: string
  created_at?: string
  updated_at?: string
}

const toApiPayload = (payload: Partial<Purchase>) => ({
  ...payload,
  supplier_id: payload.supplier_id?.toString().trim() ? payload.supplier_id : null,
})

const normalizePurchase = (raw: any): Purchase => ({
  id: String(raw?.id ?? ''),
  number: raw?.number ?? undefined,
  date: raw?.date ?? '',
  delivery_date: raw?.delivery_date ?? undefined,
  supplier_id: raw?.supplier_id ?? undefined,
  supplier_name: raw?.supplier_name ?? undefined,
  subtotal: Number(raw?.subtotal ?? 0),
  taxes: Number(raw?.taxes ?? 0),
  total: Number(raw?.total ?? 0),
  status: (raw?.status ?? 'draft') as Purchase['status'],
  lines: Array.isArray(raw?.lines) ? raw.lines : undefined,
  notes: raw?.notes ?? undefined,
  created_at: raw?.created_at ?? undefined,
  updated_at: raw?.updated_at ?? undefined,
})

export async function listPurchases(): Promise<Purchase[]> {
  const { data } = await tenantApi.get<Purchase[] | { items?: Purchase[] }>(TENANT_PURCHASES.base)
  if (Array.isArray(data)) return data.map(normalizePurchase)
  const items = (data as any)?.items
  return Array.isArray(items) ? items.map(normalizePurchase) : []
}

export async function getPurchase(id: number | string): Promise<Purchase> {
  const { data } = await tenantApi.get<Purchase>(TENANT_PURCHASES.byId(id))
  return normalizePurchase(data)
}

export async function createPurchase(payload: Omit<Purchase, 'id'>): Promise<Purchase> {
  const cleanPayload = stripOfflineMeta(payload as any)
  try {
    const response = await tenantApi.post<Purchase>(TENANT_PURCHASES.base, toApiPayload(cleanPayload), {
      headers: { 'X-Offline-Managed': '1' },
    })

    if (isOfflineQueuedResponse(response)) {
      const tempId = createOfflineTempId('purchase')
      await storeEntity('purchase', tempId, { ...cleanPayload, _op: 'create' }, 'pending')
      return normalizePurchase({
        id: tempId,
        ...cleanPayload,
        status: (cleanPayload as any)?.status || 'draft',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      })
    }

    return normalizePurchase(response.data)
  } catch (error) {
    if (isNetworkIssue(error)) {
      const tempId = createOfflineTempId('purchase')
      await storeEntity('purchase', tempId, { ...cleanPayload, _op: 'create' }, 'pending')
      return normalizePurchase({
        id: tempId,
        ...cleanPayload,
        status: (cleanPayload as any)?.status || 'draft',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      })
    }
    throw error
  }
}

export async function updatePurchase(id: number | string, payload: Partial<Omit<Purchase, 'id'>>): Promise<Purchase> {
  const cleanPayload = stripOfflineMeta(payload as any)
  try {
    const response = await tenantApi.put<Purchase>(TENANT_PURCHASES.byId(id), toApiPayload(cleanPayload), {
      headers: { 'X-Offline-Managed': '1' },
    })

    if (isOfflineQueuedResponse(response)) {
      await storeEntity('purchase', String(id), { ...cleanPayload, _op: 'update' }, 'pending')
      return normalizePurchase({
        id,
        ...(cleanPayload as any),
        updated_at: new Date().toISOString(),
      })
    }

    return normalizePurchase(response.data)
  } catch (error) {
    if (isNetworkIssue(error)) {
      await storeEntity('purchase', String(id), { ...cleanPayload, _op: 'update' }, 'pending')
      return normalizePurchase({
        id,
        ...(cleanPayload as any),
        updated_at: new Date().toISOString(),
      })
    }
    throw error
  }
}

export async function removePurchase(id: number | string): Promise<void> {
  try {
    const response = await tenantApi.delete(TENANT_PURCHASES.byId(id), { headers: { 'X-Offline-Managed': '1' } })
    if (isOfflineQueuedResponse(response)) {
      await queueDeletion('purchase', String(id))
    }
  } catch (error) {
    if (isNetworkIssue(error)) {
      await queueDeletion('purchase', String(id))
      return
    }
    throw error
  }
}

export async function receivePurchase(id: number | string): Promise<Purchase> {
  const { data } = await tenantApi.post<Purchase>(`${TENANT_PURCHASES.byId(id)}/receive`)
  return normalizePurchase(data)
}

export type ProductionDetail = {
  expense_id: string
  order_number: string
  recipe_name: string
  qty_produced: number
  materials_total: number
  indirect_total: number
  total_cost: number
  lines: {
    ingredient_name: string
    qty_consumed: number
    unit: string
    cost_unit: number
    cost_total: number
  }[]
  indirect_costs: {
    driver_name: string
    driver_unit?: string | null
    qty_actual: number
    headcount_actual: number
    rate_applied: number
    cost_total: number
    notes?: string | null
  }[]
}

const toNumber = (value: unknown): number => {
  const next = Number(value)
  return Number.isFinite(next) ? next : 0
}

const normalizeProductionDetail = (raw: any): ProductionDetail => {
  const lines = Array.isArray(raw?.lines)
    ? raw.lines.map((line: any) => {
        const qtyConsumed = toNumber(line?.qty_consumed)
        const costTotal = toNumber(line?.cost_total ?? (qtyConsumed * toNumber(line?.cost_unit)))
        const costUnit = qtyConsumed > 0
          ? toNumber(line?.cost_unit ?? (costTotal / qtyConsumed))
          : toNumber(line?.cost_unit)
        return {
          ingredient_name: String(line?.ingredient_name ?? ''),
          qty_consumed: qtyConsumed,
          unit: String(line?.unit ?? ''),
          cost_unit: costUnit,
          cost_total: costTotal,
        }
      })
    : []

  const materialsTotal = raw?.materials_total != null
    ? toNumber(raw.materials_total)
    : lines.reduce((sum, line) => sum + toNumber(line.cost_total), 0)

  const indirectCosts = Array.isArray(raw?.indirect_costs)
    ? raw.indirect_costs.map((line: any) => ({
        driver_name: String(line?.driver_name ?? ''),
        driver_unit: line?.driver_unit ?? null,
        qty_actual: toNumber(line?.qty_actual),
        headcount_actual: Math.max(1, toNumber(line?.headcount_actual) || 1),
        rate_applied: toNumber(line?.rate_applied),
        cost_total: toNumber(
          line?.cost_total
          ?? (toNumber(line?.qty_actual) * Math.max(1, toNumber(line?.headcount_actual) || 1) * toNumber(line?.rate_applied))
        ),
        notes: line?.notes ?? null,
      }))
    : []

  const indirectTotal = raw?.indirect_total != null
    ? toNumber(raw.indirect_total)
    : indirectCosts.reduce((sum, line) => sum + toNumber(line.cost_total), 0)

  const totalCost = raw?.total_cost != null
    ? toNumber(raw.total_cost)
    : toNumber(materialsTotal + indirectTotal)

  return {
    expense_id: String(raw?.expense_id ?? ''),
    order_number: String(raw?.order_number ?? ''),
    recipe_name: String(raw?.recipe_name ?? ''),
    qty_produced: toNumber(raw?.qty_produced),
    materials_total: materialsTotal,
    indirect_total: indirectTotal,
    total_cost: totalCost,
    lines,
    indirect_costs: indirectCosts,
  }
}

export async function getProductionDetail(id: string): Promise<ProductionDetail> {
  const { data } = await tenantApi.get<ProductionDetail>(`${TENANT_PURCHASES.byId(id)}/production-detail`)
  return normalizeProductionDetail(data)
}
