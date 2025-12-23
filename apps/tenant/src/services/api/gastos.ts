import api from '../../shared/api/client'
import { TENANT_GASTOS } from '@shared/endpoints'

export async function listGastos(params?: {
  page?: number
  pageSize?: number
  search?: string
  categoryId?: string
  isPaid?: boolean
  startDate?: string
  endDate?: string
  [key: string]: any
}) {
  const response = await api.get(TENANT_GASTOS.base, { params })
  return response.data
}

export async function getGasto(id: string) {
  const response = await api.get(TENANT_GASTOS.byId(id))
  return response.data
}

export async function createGasto(data: any) {
  const response = await api.post(TENANT_GASTOS.base, data)
  return response.data
}

export async function updateGasto(id: string, data: any) {
  const response = await api.put(TENANT_GASTOS.byId(id), data)
  return response.data
}

export async function deleteGasto(id: string) {
  await api.delete(TENANT_GASTOS.byId(id))
}

export async function markGastoPaid(id: string, data: any) {
  const response = await api.post(`${TENANT_GASTOS.byId(id)}/marcar-pagado`, data)
  return response.data
}

export async function getGastosByCategory(params?: {
  startDate?: string
  endDate?: string
}) {
  const response = await api.get(`${TENANT_GASTOS.base}/stats/by-category`, { params })
  return response.data
}

export async function getGastosByMonth(params?: {
  year?: number
  categoryId?: string
}) {
  const response = await api.get(`${TENANT_GASTOS.base}/stats/by-month`, { params })
  return response.data
}
