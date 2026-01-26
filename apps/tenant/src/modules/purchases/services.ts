import tenantApi from '../../shared/api/client'
import { TENANT_PURCHASES } from '@shared/endpoints'

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

const normalizeEstado = (estado?: string | null): Compra['estado'] => {
  const raw = String(estado || '').toLowerCase()
  if (raw === 'borrador') return 'draft'
  if (raw === 'enviada') return 'sent'
  if (raw === 'recibida') return 'received'
  if (raw === 'cancelada') return 'cancelled'
  if (raw === 'draft' || raw === 'sent' || raw === 'received' || raw === 'cancelled') {
    return raw as Compra['estado']
  }
  return 'draft'
}

const normalizeCompra = (compra: Compra): Compra => ({
  ...compra,
  estado: normalizeEstado((compra as any).estado),
})

export async function listCompras(): Promise<Compra[]> {
  const { data } = await tenantApi.get<Compra[] | { items?: Compra[] }>(TENANT_PURCHASES.base)
  if (Array.isArray(data)) return data.map(normalizeCompra)
  const items = (data as any)?.items
  return Array.isArray(items) ? items.map(normalizeCompra) : []
}

export async function getCompra(id: number | string): Promise<Compra> {
  const { data } = await tenantApi.get<Compra>(TENANT_PURCHASES.byId(id))
  return normalizeCompra(data)
}

export async function createCompra(payload: Omit<Compra, 'id'>): Promise<Compra> {
  const { data } = await tenantApi.post<Compra>(TENANT_PURCHASES.base, payload)
  return normalizeCompra(data)
}

export async function updateCompra(id: number | string, payload: Partial<Omit<Compra, 'id'>>): Promise<Compra> {
  const { data } = await tenantApi.put<Compra>(TENANT_PURCHASES.byId(id), payload)
  return normalizeCompra(data)
}

export async function removeCompra(id: number | string): Promise<void> {
  await tenantApi.delete(TENANT_PURCHASES.byId(id))
}

export async function recibirCompra(id: number | string): Promise<Compra> {
  const { data } = await tenantApi.post<Compra>(`${TENANT_PURCHASES.byId(id)}/recibir`)
  return normalizeCompra(data)
}
