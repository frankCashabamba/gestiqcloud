import api from '../../shared/api/client'
import { TENANT_RRHH } from '@shared/endpoints'

// === EMPLEADOS ===
export async function listEmpleados(params?: {
  page?: number
  pageSize?: number
  search?: string
  active?: boolean
  departmentId?: string
  [key: string]: any
}) {
  const response = await api.get(TENANT_RRHH.empleados.base, { params })
  return response.data
}

export async function getEmpleado(id: string) {
  const response = await api.get(TENANT_RRHH.empleados.byId(id))
  return response.data
}

export async function createEmpleado(data: any) {
  const response = await api.post(TENANT_RRHH.empleados.base, data)
  return response.data
}

export async function updateEmpleado(id: string, data: any) {
  const response = await api.put(TENANT_RRHH.empleados.byId(id), data)
  return response.data
}

export async function deleteEmpleado(id: string) {
  await api.delete(TENANT_RRHH.empleados.byId(id))
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
  const response = await api.get(TENANT_RRHH.vacaciones.base, { params })
  return response.data
}

export async function getVacacion(id: string) {
  const response = await api.get(TENANT_RRHH.vacaciones.byId(id))
  return response.data
}

export async function createVacacion(data: any) {
  const response = await api.post(TENANT_RRHH.vacaciones.base, data)
  return response.data
}

export async function aprobarVacacion(id: string, data?: any) {
  const response = await api.post(TENANT_RRHH.vacaciones.approve(id), data)
  return response.data
}

export async function rechazarVacacion(id: string, data: any) {
  const response = await api.post(TENANT_RRHH.vacaciones.reject(id), data)
  return response.data
}
