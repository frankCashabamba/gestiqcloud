/**
 * Roles Services - API calls para gestión de roles de empresa
 */
import tenantApi from '../../shared/api/client'

export type Rol = {
  id: number
  empresa_id: number
  nombre: string
  descripcion?: string
  permisos: Record<string, boolean>
  rol_base_id?: number
  creado_por_empresa: boolean
}

export type RolCreatePayload = {
  nombre: string
  descripcion?: string
  permisos: string[]
  copiar_desde_id?: number
}

export type RolUpdatePayload = {
  nombre?: string
  descripcion?: string
  permisos?: string[]
}

const BASE = '/api/roles'

export async function listRoles(): Promise<Rol[]> {
  const { data } = await tenantApi.get<Rol[]>(BASE)
  return Array.isArray(data) ? data : []
}

export async function getRol(id: number): Promise<Rol> {
  const { data } = await tenantApi.get<Rol>(`${BASE}/${id}`)
  return data
}

export async function createRol(payload: RolCreatePayload): Promise<Rol> {
  const { data } = await tenantApi.post<Rol>(BASE, payload)
  return data
}

export async function updateRol(id: number, payload: RolUpdatePayload): Promise<Rol> {
  const { data } = await tenantApi.put<Rol>(`${BASE}/${id}`, payload)
  return data
}

export async function deleteRol(id: number): Promise<void> {
  await tenantApi.delete(`${BASE}/${id}`)
}
