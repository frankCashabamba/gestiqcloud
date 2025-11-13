import api from '../../shared/api/client'

export async function listCompras(params?: {
  page?: number
  pageSize?: number
  search?: string
  status?: string
  proveedorId?: string
  [key: string]: any
}) {
  const response = await api.get('/api/v1/purchases', { params })
  return response.data
}

export async function getCompra(id: string) {
  const response = await api.get(`/api/v1/purchases/${id}`)
  return response.data
}

export async function createCompra(data: any) {
  const response = await api.post('/api/v1/purchases', data)
  return response.data
}

export async function updateCompra(id: string, data: any) {
  const response = await api.put(`/api/v1/purchases/${id}`, data)
  return response.data
}

export async function deleteCompra(id: string) {
  await api.delete(`/api/v1/purchases/${id}`)
}

export async function receiveCompra(id: string, data: any) {
  const response = await api.post(`/api/v1/purchases/${id}/receive`, data)
  return response.data
}

export async function createCompraLinea(compraId: string, data: any) {
  const response = await api.post(`/api/v1/purchases/${compraId}/lineas`, data)
  return response.data
}

export async function updateCompraLinea(compraId: string, lineaId: string, data: any) {
  const response = await api.put(`/api/v1/purchases/${compraId}/lineas/${lineaId}`, data)
  return response.data
}

export async function deleteCompraLinea(compraId: string, lineaId: string) {
  await api.delete(`/api/v1/purchases/${compraId}/lineas/${lineaId}`)
}
