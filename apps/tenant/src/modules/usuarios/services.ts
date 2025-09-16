import tenantApi from '../../shared/api/client'
import { TENANT_USUARIOS } from '@shared/endpoints'
import type { Usuario } from './types'

export async function listUsuarios(): Promise<Usuario[]> {
  const { data } = await tenantApi.get<Usuario[]>(TENANT_USUARIOS.base)
  return data || []
}

export async function getUsuario(id: number | string): Promise<Usuario> {
  const { data } = await tenantApi.get<Usuario>(TENANT_USUARIOS.byId(id))
  return data
}

export async function createUsuario(payload: Omit<Usuario, 'id'>): Promise<Usuario> {
  const { data } = await tenantApi.post<Usuario>(TENANT_USUARIOS.base, payload)
  return data
}

export async function updateUsuario(id: number | string, payload: Omit<Usuario, 'id'>): Promise<Usuario> {
  const { data } = await tenantApi.put<Usuario>(TENANT_USUARIOS.byId(id), payload)
  return data
}

export async function removeUsuario(id: number | string): Promise<void> {
  await tenantApi.delete(TENANT_USUARIOS.byId(id))
}

