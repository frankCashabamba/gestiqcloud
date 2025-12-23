import tenantApi from '../../shared/api/client'
import { TENANT_GASTOS } from '@shared/endpoints'

export type Gasto = {
  id: string
  date: string
  amount: number
  concept?: string
  supplier_id?: string
}

export type GastoStats = {
  total: number
  pending: number
}

export async function listGastos(): Promise<Gasto[]> {
  const { data } = await tenantApi.get<Gasto[] | { items?: Gasto[] }>(TENANT_GASTOS.base)
  if (Array.isArray(data)) return data
  const items = (data as any)?.items
  return Array.isArray(items) ? items : []
}

export async function getGasto(id: number | string): Promise<Gasto> {
  const { data } = await tenantApi.get<Gasto>(TENANT_GASTOS.byId(id))
  return data
}

export async function createGasto(payload: Omit<Gasto, 'id'>): Promise<Gasto> {
  const { data } = await tenantApi.post<Gasto>(TENANT_GASTOS.base, payload)
  return data
}

export async function updateGasto(id: number | string, payload: Partial<Omit<Gasto, 'id'>>): Promise<Gasto> {
  const { data } = await tenantApi.put<Gasto>(TENANT_GASTOS.byId(id), payload)
  return data
}

export async function removeGasto(id: number | string): Promise<void> {
  await tenantApi.delete(TENANT_GASTOS.byId(id))
}

export async function marcarPagado(id: number | string): Promise<Gasto> {
  const { data } = await tenantApi.post<Gasto>(`${TENANT_GASTOS.byId(id)}/pagar`)
  return data
}

export async function getGastoStats(desde?: string, hasta?: string): Promise<GastoStats> {
  const params = new URLSearchParams()
  if (desde) params.append('desde', desde)
  if (hasta) params.append('hasta', hasta)
  const { data } = await tenantApi.get<GastoStats>(`${TENANT_GASTOS.base}/stats?${params}`)
  return data
}
