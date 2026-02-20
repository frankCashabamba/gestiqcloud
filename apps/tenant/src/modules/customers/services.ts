import tenantApi from '../../shared/api/client'
import { ensureArray } from '../../shared/utils/array'
import { TENANT_CLIENTS } from '@shared/endpoints'
import { queueDeletion, storeEntity } from '../../lib/offlineStore'
import { createOfflineTempId, isNetworkIssue, isOfflineQueuedResponse, stripOfflineMeta } from '../../lib/offlineHttp'

export type Cliente = {
  id: number | string
  name: string
  // Identidad
  identificacion?: string
  identificacion_tipo?: string
  nombre_comercial?: string
  razon_social?: string
  tax_id?: string
  // Contacto
  email?: string
  phone?: string
  telefono?: string
  contacto_nombre?: string
  contacto_email?: string
  contacto_telefono?: string
  whatsapp?: string
  website?: string
  // Dirección
  address?: string
  direccion?: string
  direccion2?: string
  city?: string
  localidad?: string
  state?: string
  provincia?: string
  ciudad?: string
  pais?: string
  codigo_postal?: string
  // Envío
  envio_direccion?: string
  envio_localidad?: string
  envio_provincia?: string
  envio_pais?: string
  envio_codigo_postal?: string
  // Comerciales
  payment_terms_days?: number
  credit_limit?: number
  descuento_pct?: number
  moneda?: string
  idioma?: string
  // Gestión
  notas?: string
  tags?: string[]
  bloqueado?: boolean
  is_wholesale?: boolean
}

export async function listClientes(): Promise<Cliente[]> {
  const { data } = await tenantApi.get<Cliente[] | { items?: Cliente[] }>(TENANT_CLIENTS.base)
  return ensureArray<Cliente>(data)
}

export async function getCliente(id: number | string): Promise<Cliente> {
  const { data } = await tenantApi.get<Cliente>(TENANT_CLIENTS.byId(id))
  return data
}

export async function createCliente(payload: Omit<Cliente, 'id'>): Promise<Cliente> {
  const cleanPayload = stripOfflineMeta(payload as any)
  try {
    const response = await tenantApi.post<Cliente>(TENANT_CLIENTS.base, cleanPayload, { headers: { 'X-Offline-Managed': '1' } })
    if (isOfflineQueuedResponse(response)) {
      const tempId = createOfflineTempId('customer')
      await storeEntity('customer', tempId, { ...cleanPayload, _op: 'create' }, 'pending')
      return { id: tempId, ...(cleanPayload as any) }
    }
    return response.data
  } catch (error) {
    if (isNetworkIssue(error)) {
      const tempId = createOfflineTempId('customer')
      await storeEntity('customer', tempId, { ...cleanPayload, _op: 'create' }, 'pending')
      return { id: tempId, ...(cleanPayload as any) }
    }
    throw error
  }
}

export async function updateCliente(id: number | string, payload: Omit<Cliente, 'id'>): Promise<Cliente> {
  const cleanPayload = stripOfflineMeta(payload as any)
  try {
    const response = await tenantApi.put<Cliente>(TENANT_CLIENTS.byId(id), cleanPayload, { headers: { 'X-Offline-Managed': '1' } })
    if (isOfflineQueuedResponse(response)) {
      await storeEntity('customer', String(id), { ...cleanPayload, _op: 'update' }, 'pending')
      return { id, ...(cleanPayload as any) } as Cliente
    }
    return response.data
  } catch (error) {
    if (isNetworkIssue(error)) {
      await storeEntity('customer', String(id), { ...cleanPayload, _op: 'update' }, 'pending')
      return { id, ...(cleanPayload as any) } as Cliente
    }
    throw error
  }
}

export async function removeCliente(id: number | string): Promise<void> {
  try {
    const response = await tenantApi.delete(TENANT_CLIENTS.byId(id), { headers: { 'X-Offline-Managed': '1' } })
    if (isOfflineQueuedResponse(response)) {
      await queueDeletion('customer', String(id))
    }
  } catch (error) {
    if (isNetworkIssue(error)) {
      await queueDeletion('customer', String(id))
      return
    }
    throw error
  }
}
