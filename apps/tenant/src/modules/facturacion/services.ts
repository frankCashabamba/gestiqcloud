import tenantApi from '../../shared/api/client'
import { TENANT_FACTURACION, TENANT_FACTURAE } from '@shared/endpoints'

export type Factura = {
  id: number | string
  fecha: string
  cliente_id?: number | string
  total: number
  estado?: string
}

export async function listFacturas(): Promise<Factura[]> {
  const { data } = await tenantApi.get<Factura[]>(TENANT_FACTURACION.base)
  return data || []
}
export async function getFactura(id: number | string): Promise<Factura> {
  const { data } = await tenantApi.get<Factura>(TENANT_FACTURACION.byId(id))
  return data
}
export async function createFactura(payload: Omit<Factura,'id'>): Promise<Factura> {
  const { data } = await tenantApi.post<Factura>(TENANT_FACTURACION.base, payload)
  return data
}
export async function updateFactura(id: number | string, payload: Omit<Factura,'id'>): Promise<Factura> {
  const { data } = await tenantApi.put<Factura>(TENANT_FACTURACION.byId(id), payload)
  return data
}
export async function removeFactura(id: number | string): Promise<void> {
  await tenantApi.delete(TENANT_FACTURACION.byId(id))
}

export async function exportarFacturae(id: number | string): Promise<Blob> {
  const { data } = await tenantApi.get(TENANT_FACTURAE.base + `/${id}`, { responseType: 'blob' } as any)
  return data as Blob
}

