import tenantApi from '../../shared/api/client'
import { TENANT_COMPRAS } from '@shared/endpoints'

export type CompraLinea = {
  id?: number | string
  producto_id: number | string
  cantidad: number
  precio_unitario: number
  subtotal: number
}

export type Compra = {
  id: number | string
  numero?: string
  fecha: string
  fecha_entrega?: string
  proveedor_id?: number | string
  proveedor_nombre?: string
  subtotal: number
  impuesto: number
  total: number
  estado: 'draft' | 'sent' | 'received' | 'cancelled'
  lineas?: CompraLinea[]
  notas?: string
  created_at?: string
  updated_at?: string
}

export async function listCompras(): Promise<Compra[]> {
  const { data } = await tenantApi.get<Compra[] | { items?: Compra[] }>(TENANT_COMPRAS.base)
  if (Array.isArray(data)) return data
  const items = (data as any)?.items
  return Array.isArray(items) ? items : []
}

export async function getCompra(id: number | string): Promise<Compra> {
  const { data } = await tenantApi.get<Compra>(TENANT_COMPRAS.byId(id))
  return data
}

export async function createCompra(payload: Omit<Compra, 'id'>): Promise<Compra> {
  const { data } = await tenantApi.post<Compra>(TENANT_COMPRAS.base, payload)
  return data
}

export async function updateCompra(id: number | string, payload: Partial<Omit<Compra, 'id'>>): Promise<Compra> {
  const { data } = await tenantApi.put<Compra>(TENANT_COMPRAS.byId(id), payload)
  return data
}

export async function removeCompra(id: number | string): Promise<void> {
  await tenantApi.delete(TENANT_COMPRAS.byId(id))
}

export async function recibirCompra(id: number | string): Promise<Compra> {
  const { data } = await tenantApi.post<Compra>(`${TENANT_COMPRAS.byId(id)}/recibir`)
  return data
}
