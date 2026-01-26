import api from '../../shared/api/client'
import { TENANT_PURCHASES } from '@shared/endpoints'

export async function listCompras(params?: {
  page?: number
  pageSize?: number
  search?: string
  status?: string
  proveedorId?: string
  [key: string]: any
}) {
  const response = await api.get(TENANT_PURCHASES.base, { params })
  return response.data
}

export async function getCompra(id: string) {
  const response = await api.get(TENANT_PURCHASES.byId(id))
  return response.data
}

export async function createCompra(data: any) {
  const response = await api.post(TENANT_PURCHASES.base, data)
  return response.data
}

export async function updateCompra(id: string, data: any) {
  const response = await api.put(TENANT_PURCHASES.byId(id), data)
  return response.data
}

export async function deleteCompra(id: string) {
  await api.delete(TENANT_PURCHASES.byId(id))
}

export async function receiveCompra(id: string, data: any) {
  const response = await api.post(`${TENANT_PURCHASES.byId(id)}/recibir`, data)
  return response.data
}

export async function createCompraLinea(compraId: string, data: any) {
  const response = await api.post(`${TENANT_PURCHASES.byId(compraId)}/lineas`, data)
  return response.data
}

export async function updateCompraLinea(compraId: string, lineaId: string, data: any) {
  const response = await api.put(`${TENANT_PURCHASES.byId(compraId)}/lineas/${lineaId}`, data)
  return response.data
}

export async function deleteCompraLinea(compraId: string, lineaId: string) {
  await api.delete(`${TENANT_PURCHASES.byId(compraId)}/lineas/${lineaId}`)
}
