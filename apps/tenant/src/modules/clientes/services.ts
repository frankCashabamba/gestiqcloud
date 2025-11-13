import tenantApi from '../../shared/api/client'
import { ensureArray } from '../../shared/utils/array'
import { TENANT_CLIENTES } from '@shared/endpoints'

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
}

export async function listClientes(): Promise<Cliente[]> {
  const { data } = await tenantApi.get<Cliente[] | { items?: Cliente[] }>(TENANT_CLIENTES.base)
  return ensureArray<Cliente>(data)
}

export async function getCliente(id: number | string): Promise<Cliente> {
  const { data } = await tenantApi.get<Cliente>(TENANT_CLIENTES.byId(id))
  return data
}

export async function createCliente(payload: Omit<Cliente, 'id'>): Promise<Cliente> {
  const { data } = await tenantApi.post<Cliente>(TENANT_CLIENTES.base, payload)
  return data
}

export async function updateCliente(id: number | string, payload: Omit<Cliente, 'id'>): Promise<Cliente> {
  const { data } = await tenantApi.put<Cliente>(TENANT_CLIENTES.byId(id), payload)
  return data
}

export async function removeCliente(id: number | string): Promise<void> {
  await tenantApi.delete(TENANT_CLIENTES.byId(id))
}
