import api from '../../shared/api/client'
import { TENANT_VENTAS } from '@shared/endpoints'

export async function listVentas(params?: {
  page?: number
  pageSize?: number
  search?: string
  status?: string
  [key: string]: any
}) {
  const response = await api.get(TENANT_VENTAS.base, { params })
  return response.data
}

export async function getVenta(id: string) {
  const response = await api.get(TENANT_VENTAS.byId(id))
  return response.data
}

export async function createVenta(data: any) {
  const response = await api.post(TENANT_VENTAS.base, data)
  return response.data
}

export async function updateVenta(id: string, data: any) {
  const response = await api.put(TENANT_VENTAS.byId(id), data)
  return response.data
}

export async function deleteVenta(id: string) {
  await api.delete(TENANT_VENTAS.byId(id))
}

export async function convertToInvoice(id: string, data: any) {
  const response = await api.post(`${TENANT_VENTAS.byId(id)}/invoice`, data)
  return response.data
}

export async function getVentasStats(params?: {
  startDate?: string
  endDate?: string
  groupBy?: string
}) {
  const response = await api.get(`${TENANT_VENTAS.base}/stats`, { params })
  return response.data
}
