import api from '../../shared/api/client'

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
  const response = await api.get('/api/v1/expenses', { params })
  return response.data
}

export async function getGasto(id: string) {
  const response = await api.get(`/api/v1/expenses/${id}`)
  return response.data
}

export async function createGasto(data: any) {
  const response = await api.post('/api/v1/expenses', data)
  return response.data
}

export async function updateGasto(id: string, data: any) {
  const response = await api.put(`/api/v1/expenses/${id}`, data)
  return response.data
}

export async function deleteGasto(id: string) {
  await api.delete(`/api/v1/expenses/${id}`)
}

export async function markGastoPaid(id: string, data: any) {
  const response = await api.post(`/api/v1/expenses/${id}/mark-paid`, data)
  return response.data
}

export async function getGastosByCategory(params?: {
  startDate?: string
  endDate?: string
}) {
  const response = await api.get('/api/v1/expenses/stats/by-category', { params })
  return response.data
}

export async function getGastosByMonth(params?: {
  year?: number
  categoryId?: string
}) {
  const response = await api.get('/api/v1/expenses/stats/by-month', { params })
  return response.data
}
