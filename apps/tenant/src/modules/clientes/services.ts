import tenantApi from '../../shared/api/client'
import { ensureArray } from '../../shared/utils/array'
import { TENANT_CLIENTES } from '@shared/endpoints'

export type Cliente = {
  id: number | string
  nombre: string
  email?: string
  telefono?: string
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
