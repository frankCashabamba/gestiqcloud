import tenantApi from '../../shared/api/client'
import { TENANT_COMPRAS } from '@shared/endpoints'

export type Compra = {
  id: number | string
  fecha: string
  proveedor_id?: number | string
  total: number
  estado?: string
}

export async function listCompras(): Promise<Compra[]> {
  const { data } = await tenantApi.get<Compra[]>(TENANT_COMPRAS.base)
  return data || []
}

export async function getCompra(id: number | string): Promise<Compra> {
  const { data } = await tenantApi.get<Compra>(TENANT_COMPRAS.byId(id))
  return data
}

export async function createCompra(payload: Omit<Compra, 'id'>): Promise<Compra> {
  const { data } = await tenantApi.post<Compra>(TENANT_COMPRAS.base, payload)
  return data
}

export async function updateCompra(id: number | string, payload: Omit<Compra, 'id'>): Promise<Compra> {
  const { data } = await tenantApi.put<Compra>(TENANT_COMPRAS.byId(id), payload)
  return data
}

export async function removeCompra(id: number | string): Promise<void> {
  await tenantApi.delete(TENANT_COMPRAS.byId(id))
}

