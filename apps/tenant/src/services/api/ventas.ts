import api from '../../shared/api/client'

export async function listVentas(params?: {
  page?: number
  pageSize?: number
  search?: string
  status?: string
  [key: string]: any
}) {
  const response = await api.get('/api/v1/sales', { params })
  return response.data
}

export async function getVenta(id: string) {
  const response = await api.get(`/api/v1/sales/${id}`)
  return response.data
}

export async function createVenta(data: any) {
  const response = await api.post('/api/v1/sales', data)
  return response.data
}

export async function updateVenta(id: string, data: any) {
  const response = await api.put(`/api/v1/sales/${id}`, data)
  return response.data
}

export async function deleteVenta(id: string) {
  await api.delete(`/api/v1/sales/${id}`)
}

export async function convertToInvoice(id: string, data: any) {
  const response = await api.post(`/api/v1/sales/${id}/convert-to-invoice`, data)
  return response.data
}

export async function getVentasStats(params?: {
  startDate?: string
  endDate?: string
  groupBy?: string
}) {
  const response = await api.get('/api/v1/sales/stats', { params })
  return response.data
}
