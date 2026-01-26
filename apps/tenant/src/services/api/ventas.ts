import api from '../../shared/api/client'
import { TENANT_SALES } from '@shared/endpoints'

export async function listVentas(params?: {
  page?: number
  pageSize?: number
  search?: string
  status?: string
  [key: string]: any
}) {
  const response = await api.get(TENANT_SALES.base, { params })
  return response.data
}

export async function getVenta(id: string) {
  const response = await api.get(TENANT_SALES.byId(id))
  return response.data
}

export async function createVenta(data: any) {
  const response = await api.post(TENANT_SALES.base, data)
  return response.data
}

export async function updateVenta(id: string, data: any) {
  const response = await api.put(TENANT_SALES.byId(id), data)
  return response.data
}

export async function deleteVenta(id: string) {
  await api.delete(TENANT_SALES.byId(id))
}

export async function convertToInvoice(id: string, data: any) {
  const response = await api.post(`${TENANT_SALES.byId(id)}/invoice`, data)
  return response.data
}

export async function getVentasStats(params?: {
  startDate?: string
  endDate?: string
  groupBy?: string
}) {
  const response = await api.get(`${TENANT_SALES.base}/stats`, { params })
  return response.data
}
