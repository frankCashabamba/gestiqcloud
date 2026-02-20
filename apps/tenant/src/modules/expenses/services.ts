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
  invoice_number?: string
  notes?: string
  created_at?: string
  updated_at?: string
}

export type GastoStats = {
  total: number
  pending: number
}

const normalizeGasto = (raw: any): Gasto => ({
  id: String(raw?.id ?? ''),
  date: raw?.date ?? raw?.fecha ?? '',
  amount: Number(raw?.amount ?? raw?.monto ?? 0),
  category: raw?.category ?? raw?.categoria,
  subcategory: raw?.subcategory ?? raw?.subcategoria,
  concept: raw?.concept ?? raw?.concepto,
  payment_method: raw?.payment_method ?? raw?.forma_pago,
  supplier_id: raw?.supplier_id ?? raw?.proveedor_id,
  supplier_name: raw?.supplier_name ?? raw?.proveedor_nombre,
  status: raw?.status ?? raw?.estado,
  invoice_number: raw?.invoice_number ?? raw?.factura_numero,
  notes: raw?.notes ?? raw?.notas,
  created_at: raw?.created_at,
  updated_at: raw?.updated_at,
})

const toApiPayload = (payload: Partial<Gasto>) => ({
  ...payload,
  fecha: payload.date,
  monto: payload.amount,
  categoria: payload.category,
  subcategoria: payload.subcategory,
  concepto: payload.concept,
  forma_pago: payload.payment_method,
  proveedor_id: payload.supplier_id,
  proveedor_nombre: payload.supplier_name,
  estado: payload.status,
  factura_numero: payload.invoice_number,
  notas: payload.notes,
})

export async function listGastos(): Promise<Gasto[]> {
  const { data } = await tenantApi.get<Gasto[] | { items?: Gasto[] }>(TENANT_EXPENSES.base)
  if (Array.isArray(data)) return data.map(normalizeGasto)
  const items = (data as any)?.items
  return Array.isArray(items) ? items.map(normalizeGasto) : []
}

export async function getGasto(id: number | string): Promise<Gasto> {
  const { data } = await tenantApi.get<Gasto>(TENANT_EXPENSES.byId(id))
  return normalizeGasto(data)
}

export async function createGasto(payload: Omit<Gasto, 'id'>): Promise<Gasto> {
  const apiPayload = stripOfflineMeta(toApiPayload(payload) as any)
  try {
    const response = await tenantApi.post<Gasto>(TENANT_EXPENSES.base, apiPayload, { headers: { 'X-Offline-Managed': '1' } })

    if (isOfflineQueuedResponse(response)) {
      const tempId = createOfflineTempId('expense')
      await storeEntity('expense', tempId, { ...apiPayload, _op: 'create' }, 'pending')
      return normalizeGasto({
        id: tempId,
        ...apiPayload,
        estado: (apiPayload as any)?.estado || 'pending',
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
        estado: (apiPayload as any)?.estado || 'pending',
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
    const response = await tenantApi.put<Gasto>(TENANT_EXPENSES.byId(id), apiPayload, { headers: { 'X-Offline-Managed': '1' } })

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
    const response = await tenantApi.delete(TENANT_EXPENSES.byId(id), { headers: { 'X-Offline-Managed': '1' } })
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
