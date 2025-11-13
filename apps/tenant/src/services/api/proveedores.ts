import api from '../../shared/api/client'

export async function listProveedores(params?: {
  page?: number
  pageSize?: number
  search?: string
  active?: boolean
  [key: string]: any
}) {
  const response = await api.get('/api/v1/suppliers', { params })
  return response.data
}

export async function getProveedor(id: string) {
  const response = await api.get(`/api/v1/suppliers/${id}`)
  return response.data
}

export async function createProveedor(data: any) {
  const response = await api.post('/api/v1/suppliers', data)
  return response.data
}

export async function updateProveedor(id: string, data: any) {
  const response = await api.put(`/api/v1/suppliers/${id}`, data)
  return response.data
}

export async function deleteProveedor(id: string) {
  await api.delete(`/api/v1/suppliers/${id}`)
}

export async function listContactos(proveedorId: string) {
  const response = await api.get(`/api/v1/suppliers/${proveedorId}/contactos`)
  return response.data
}

export async function createContacto(proveedorId: string, data: any) {
  const response = await api.post(`/api/v1/suppliers/${proveedorId}/contactos`, data)
  return response.data
}

export async function updateContacto(proveedorId: string, contactoId: string, data: any) {
  const response = await api.put(`/api/v1/suppliers/${proveedorId}/contactos/${contactoId}`, data)
  return response.data
}

export async function deleteContacto(proveedorId: string, contactoId: string) {
  await api.delete(`/api/v1/suppliers/${proveedorId}/contactos/${contactoId}`)
}

export async function getComprasByProveedor(proveedorId: string, params?: {
  page?: number
  pageSize?: number
  startDate?: string
  endDate?: string
}) {
  const response = await api.get(`/api/v1/suppliers/${proveedorId}/purchases`, { params })
  return response.data
}
