import tenantApi from '../../shared/api/client'
import { TENANT_PURCHASES } from '@shared/endpoints'
import { queueDeletion, storeEntity } from '../../lib/offlineStore'
import { createOfflineTempId, isNetworkIssue, isOfflineQueuedResponse, stripOfflineMeta } from '../../lib/offlineHttp'

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
  const cleanPayload = stripOfflineMeta(payload as any)
  try {
    const response = await tenantApi.post<Compra>(TENANT_PURCHASES.base, cleanPayload, { headers: { 'X-Offline-Managed': '1' } })

    if (isOfflineQueuedResponse(response)) {
      const tempId = createOfflineTempId('purchase')
      await storeEntity('purchase', tempId, { ...cleanPayload, _op: 'create' }, 'pending')
      return normalizeCompra({
        id: tempId,
        ...cleanPayload,
        estado: payload.estado || 'draft',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      } as Compra)
    }

    return normalizeCompra(response.data)
  } catch (error) {
    if (isNetworkIssue(error)) {
      const tempId = createOfflineTempId('purchase')
      await storeEntity('purchase', tempId, { ...cleanPayload, _op: 'create' }, 'pending')
      return normalizeCompra({
        id: tempId,
        ...cleanPayload,
        estado: payload.estado || 'draft',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      } as Compra)
    }
    throw error
  }
}

export async function updateCompra(id: number | string, payload: Partial<Omit<Compra, 'id'>>): Promise<Compra> {
  const cleanPayload = stripOfflineMeta(payload as any)
  try {
    const response = await tenantApi.put<Compra>(TENANT_PURCHASES.byId(id), cleanPayload, { headers: { 'X-Offline-Managed': '1' } })

    if (isOfflineQueuedResponse(response)) {
      await storeEntity('purchase', String(id), { ...cleanPayload, _op: 'update' }, 'pending')
      return normalizeCompra({
        id,
        ...(cleanPayload as any),
        estado: (payload as any)?.estado || 'draft',
        updated_at: new Date().toISOString(),
      } as Compra)
    }

    return normalizeCompra(response.data)
  } catch (error) {
    if (isNetworkIssue(error)) {
      await storeEntity('purchase', String(id), { ...cleanPayload, _op: 'update' }, 'pending')
      return normalizeCompra({
        id,
        ...(cleanPayload as any),
        estado: (payload as any)?.estado || 'draft',
        updated_at: new Date().toISOString(),
      } as Compra)
    }
    throw error
  }
}

export async function removeCompra(id: number | string): Promise<void> {
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

export async function recibirCompra(id: number | string): Promise<Compra> {
  const { data } = await tenantApi.post<Compra>(`${TENANT_PURCHASES.byId(id)}/recibir`)
  return normalizeCompra(data)
}
