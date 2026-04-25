import tenantApi from '../../shared/api/client'
import { TENANT_EXPENSES } from '@shared/endpoints'
import { queueDeletion, storeEntity } from '../../lib/offlineStore'
import { createOfflineTempId, isNetworkIssue, isOfflineQueuedResponse, stripOfflineMeta } from '../../lib/offlineHttp'

export type Gasto = {
  id: string
  date: string
  amount: number
  category?: string
  subcategory?: string
  concept?: string
  payment_method?: string
  supplier_id?: string
  supplier_name?: string
  status?: string
  paid_amount?: number | null
  pending_amount?: number | null
  invoice_number?: string
  notes?: string
  created_at?: string
  updated_at?: string
}

export type GastoStats = {
  total: number
  pending: number
}

const toNumber = (value: unknown): number => {
  const next = Number(value)
  return Number.isFinite(next) ? next : 0
}

const normalizeGasto = (raw: any): Gasto => ({
  id: String(raw?.id ?? ''),
  date: raw?.date ?? '',
  amount: Number(raw?.amount ?? 0),
  category: raw?.category ?? undefined,
  subcategory: raw?.subcategory ?? undefined,
  concept: raw?.concept ?? undefined,
  payment_method: raw?.payment_method ?? undefined,
  supplier_id: raw?.supplier_id ?? undefined,
  supplier_name: raw?.supplier_name ?? undefined,
  status: raw?.status ?? 'draft',
  invoice_number: raw?.invoice_number ?? undefined,
  notes: raw?.notes ?? undefined,
  created_at: raw?.created_at,
  updated_at: raw?.updated_at,
})

const toApiPayload = (payload: Partial<Gasto>) => ({
  ...payload,
  date: payload.date,
  amount: payload.amount,
  category: payload.category,
  subcategory: payload.subcategory,
  concept: payload.concept,
  payment_method: payload.payment_method,
  ...(payload.supplier_id?.trim() ? { supplier_id: payload.supplier_id.trim() } : {}),
  supplier_name: payload.supplier_name,
  status: payload.status,
  invoice_number: payload.invoice_number,
  notes: payload.notes,
})

export async function listGastos(): Promise<Gasto[]> {
  const { data } = await tenantApi.get<Gasto[] | { items?: Gasto[] }>(TENANT_EXPENSES.base)
  if (Array.isArray(data)) return data.map(normalizeGasto)
  const items = (data as { items?: Gasto[] }).items
  return Array.isArray(items) ? items.map(normalizeGasto) : []
}

export async function getGasto(id: number | string): Promise<Gasto> {
  const { data } = await tenantApi.get<Gasto>(TENANT_EXPENSES.byId(id))
  return normalizeGasto(data)
}

export async function createGasto(payload: Omit<Gasto, 'id'>): Promise<Gasto> {
  const apiPayload = stripOfflineMeta(toApiPayload(payload) as any)
  try {
    const response = await tenantApi.post<Gasto>(TENANT_EXPENSES.base, apiPayload)

    if (isOfflineQueuedResponse(response)) {
      const tempId = createOfflineTempId('expense')
      await storeEntity('expense', tempId, { ...apiPayload, _op: 'create' }, 'pending')
      return normalizeGasto({
        id: tempId,
        ...apiPayload,
        status: (apiPayload as any)?.status || 'draft',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      })
    }

    return normalizeGasto(response.data)
  } catch (error) {
    if (isNetworkIssue(error)) {
      const tempId = createOfflineTempId('expense')
      await storeEntity('expense', tempId, { ...apiPayload, _op: 'create' }, 'pending')
      return normalizeGasto({
        id: tempId,
        ...apiPayload,
        status: (apiPayload as any)?.status || 'draft',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      })
    }
    throw error
  }
}

export async function updateGasto(id: number | string, payload: Partial<Omit<Gasto, 'id'>>): Promise<Gasto> {
  const apiPayload = stripOfflineMeta(toApiPayload(payload) as any)
  try {
    const response = await tenantApi.put<Gasto>(TENANT_EXPENSES.byId(id), apiPayload)

    if (isOfflineQueuedResponse(response)) {
      await storeEntity('expense', String(id), { ...apiPayload, _op: 'update' }, 'pending')
      return normalizeGasto({
        id: String(id),
        ...apiPayload,
        updated_at: new Date().toISOString(),
      })
    }

    return normalizeGasto(response.data)
  } catch (error) {
    if (isNetworkIssue(error)) {
      await storeEntity('expense', String(id), { ...apiPayload, _op: 'update' }, 'pending')
      return normalizeGasto({
        id: String(id),
        ...apiPayload,
        updated_at: new Date().toISOString(),
      })
    }
    throw error
  }
}

export async function removeGasto(id: number | string): Promise<void> {
  try {
    const response = await tenantApi.delete(TENANT_EXPENSES.byId(id))
    if (isOfflineQueuedResponse(response)) {
      await queueDeletion('expense', String(id))
    }
  } catch (error) {
    if (isNetworkIssue(error)) {
      await queueDeletion('expense', String(id))
      return
    }
    throw error
  }
}

export async function marcarPagado(id: number | string): Promise<Gasto> {
  const { data } = await tenantApi.post<Gasto>(`${TENANT_EXPENSES.byId(id)}/pagar`)
  return normalizeGasto(data)
}

export async function getGastoStats(desde?: string, hasta?: string): Promise<GastoStats> {
  const params = new URLSearchParams()
  if (desde) params.append('desde', desde)
  if (hasta) params.append('hasta', hasta)
  const { data } = await tenantApi.get<GastoStats>(`${TENANT_EXPENSES.base}/stats?${params}`)
  return data
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

const normalizeProductionDetail = (raw: any): ProductionDetail => {
  const lines = Array.isArray(raw?.lines)
    ? raw.lines.map((line: any) => {
        const qtyConsumed = toNumber(line?.qty_consumed)
        const costTotal = toNumber(
          line?.cost_total ?? (qtyConsumed * toNumber(line?.cost_unit))
        )
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
  const { data } = await tenantApi.get<ProductionDetail>(`${TENANT_EXPENSES.byId(id)}/production-detail`)
  return normalizeProductionDetail(data)
}
