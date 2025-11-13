import api from '../../shared/api/client'

// === EMPLEADOS ===
export async function listEmpleados(params?: {
  page?: number
  pageSize?: number
  search?: string
  active?: boolean
  departmentId?: string
  [key: string]: any
}) {
  const response = await api.get('/api/v1/rrhh/empleados', { params })
  return response.data
}

export async function getEmpleado(id: string) {
  const response = await api.get(`/api/v1/rrhh/empleados/${id}`)
  return response.data
}

export async function createEmpleado(data: any) {
  const response = await api.post('/api/v1/rrhh/empleados', data)
  return response.data
}

export async function updateEmpleado(id: string, data: any) {
  const response = await api.put(`/api/v1/rrhh/empleados/${id}`, data)
  return response.data
}

export async function deleteEmpleado(id: string) {
  await api.delete(`/api/v1/rrhh/empleados/${id}`)
}

// === VACACIONES ===
export async function listVacaciones(params?: {
  page?: number
  pageSize?: number
  empleadoId?: string
  status?: string
  startDate?: string
  endDate?: string
  [key: string]: any
}) {
  const response = await api.get('/api/v1/rrhh/vacaciones', { params })
  return response.data
}

export async function getVacacion(id: string) {
  const response = await api.get(`/api/v1/rrhh/vacaciones/${id}`)
  return response.data
}

export async function createVacacion(data: any) {
  const response = await api.post('/api/v1/rrhh/vacaciones', data)
  return response.data
}

export async function aprobarVacacion(id: string, data?: any) {
  const response = await api.post(`/api/v1/rrhh/vacaciones/${id}/aprobar`, data)
  return response.data
}

export async function rechazarVacacion(id: string, data: any) {
  const response = await api.post(`/api/v1/rrhh/vacaciones/${id}/rechazar`, data)
  return response.data
}
