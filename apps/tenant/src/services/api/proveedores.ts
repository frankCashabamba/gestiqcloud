import api from '../../shared/api/client'
import { TENANT_PROVEEDORES } from '@shared/endpoints'

export async function listProveedores(params?: {
  page?: number
  pageSize?: number
  search?: string
  active?: boolean
  [key: string]: any
}) {
  const response = await api.get(TENANT_PROVEEDORES.base, { params })
  return response.data
}

export async function getProveedor(id: string) {
  const response = await api.get(TENANT_PROVEEDORES.byId(id))
  return response.data
}

export async function createProveedor(data: any) {
  const response = await api.post(TENANT_PROVEEDORES.base, data)
  return response.data
}

export async function updateProveedor(id: string, data: any) {
  const response = await api.put(TENANT_PROVEEDORES.byId(id), data)
  return response.data
}

export async function deleteProveedor(id: string) {
  await api.delete(TENANT_PROVEEDORES.byId(id))
}

export async function listContactos(proveedorId: string) {
  const response = await api.get(`${TENANT_PROVEEDORES.byId(proveedorId)}/contactos`)
  return response.data
}

export async function createContacto(proveedorId: string, data: any) {
  const response = await api.post(`${TENANT_PROVEEDORES.byId(proveedorId)}/contactos`, data)
  return response.data
}

export async function updateContacto(proveedorId: string, contactoId: string, data: any) {
  const response = await api.put(`${TENANT_PROVEEDORES.byId(proveedorId)}/contactos/${contactoId}`, data)
  return response.data
}

export async function deleteContacto(proveedorId: string, contactoId: string) {
  await api.delete(`${TENANT_PROVEEDORES.byId(proveedorId)}/contactos/${contactoId}`)
}

export async function getComprasByProveedor(proveedorId: string, params?: {
  page?: number
  pageSize?: number
  startDate?: string
  endDate?: string
}) {
  const response = await api.get(`${TENANT_PROVEEDORES.byId(proveedorId)}/purchases`, { params })
  return response.data
}
