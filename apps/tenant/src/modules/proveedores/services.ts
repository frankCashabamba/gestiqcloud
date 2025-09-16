import tenantApi from '../../shared/api/client'
import { TENANT_PROVEEDORES } from '@shared/endpoints'

export type Proveedor = {
  id: number | string
  nombre: string
  email?: string
  telefono?: string
}

export async function listProveedores(): Promise<Proveedor[]> {
  const { data } = await tenantApi.get<Proveedor[]>(TENANT_PROVEEDORES.base)
  return data || []
}

export async function getProveedor(id: number | string): Promise<Proveedor> {
  const { data } = await tenantApi.get<Proveedor>(TENANT_PROVEEDORES.byId(id))
  return data
}

export async function createProveedor(payload: Omit<Proveedor, 'id'>): Promise<Proveedor> {
  const { data } = await tenantApi.post<Proveedor>(TENANT_PROVEEDORES.base, payload)
  return data
}

export async function updateProveedor(id: number | string, payload: Omit<Proveedor, 'id'>): Promise<Proveedor> {
  const { data } = await tenantApi.put<Proveedor>(TENANT_PROVEEDORES.byId(id), payload)
  return data
}

export async function removeProveedor(id: number | string): Promise<void> {
  await tenantApi.delete(TENANT_PROVEEDORES.byId(id))
}

