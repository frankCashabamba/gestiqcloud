import tenantApi from '../../shared/api/client'
import { TENANT_GASTOS } from '@shared/endpoints'

export type Gasto = {
  id: number | string
  fecha: string
  proveedor_id?: number | string
  monto: number
  concepto?: string
}

export async function listGastos(): Promise<Gasto[]> {
  const { data } = await tenantApi.get<Gasto[]>(TENANT_GASTOS.base)
  return data || []
}
export async function getGasto(id: number | string): Promise<Gasto> {
  const { data } = await tenantApi.get<Gasto>(TENANT_GASTOS.byId(id))
  return data
}
export async function createGasto(payload: Omit<Gasto,'id'>): Promise<Gasto> {
  const { data } = await tenantApi.post<Gasto>(TENANT_GASTOS.base, payload)
  return data
}
export async function updateGasto(id: number | string, payload: Omit<Gasto,'id'>): Promise<Gasto> {
  const { data } = await tenantApi.put<Gasto>(TENANT_GASTOS.byId(id), payload)
  return data
}
export async function removeGasto(id: number | string): Promise<void> {
  await tenantApi.delete(TENANT_GASTOS.byId(id))
}

