import tenantApi from '../../shared/api/client'
import { TENANT_VENTAS } from '@shared/endpoints'

export type Venta = {
  id: number | string
  fecha: string
  cliente_id?: number | string
  total: number
  estado?: string
}

export async function listVentas(): Promise<Venta[]> {
  const { data } = await tenantApi.get<Venta[] | { items?: Venta[] }>(TENANT_VENTAS.base)
  if (Array.isArray(data)) return data
  const items = (data as any)?.items
  return Array.isArray(items) ? items : []
}

export async function getVenta(id: number | string): Promise<Venta> {
  const { data } = await tenantApi.get<Venta>(TENANT_VENTAS.byId(id))
  return data
}

export async function createVenta(payload: Omit<Venta, 'id'>): Promise<Venta> {
  const { data } = await tenantApi.post<Venta>(TENANT_VENTAS.base, payload)
  return data
}

export async function updateVenta(id: number | string, payload: Omit<Venta, 'id'>): Promise<Venta> {
  const { data } = await tenantApi.put<Venta>(TENANT_VENTAS.byId(id), payload)
  return data
}

export async function removeVenta(id: number | string): Promise<void> {
  await tenantApi.delete(TENANT_VENTAS.byId(id))
}
