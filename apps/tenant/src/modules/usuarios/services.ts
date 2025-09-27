import tenantApi from '../../shared/api/client'
import { TENANT_USUARIOS } from '@shared/endpoints'
import type {
  Usuario,
  UsuarioCreatePayload,
  UsuarioUpdatePayload,
  ModuloOption,
  RolOption,
} from './types'

export async function listUsuarios(): Promise<Usuario[]> {
  const { data } = await tenantApi.get<Usuario[]>(TENANT_USUARIOS.base)
  return data ?? []
}

export async function getUsuario(id: number | string): Promise<Usuario> {
  const { data } = await tenantApi.get<Usuario>(TENANT_USUARIOS.byId(id))
  return data
}

export async function createUsuario(payload: UsuarioCreatePayload): Promise<Usuario> {
  const { data } = await tenantApi.post<Usuario>(TENANT_USUARIOS.base, payload)
  return data
}

export async function updateUsuario(id: number | string, payload: UsuarioUpdatePayload): Promise<Usuario> {
  const { data } = await tenantApi.patch<Usuario>(TENANT_USUARIOS.byId(id), payload)
  return data
}

export async function removeUsuario(id: number | string): Promise<void> {
  await tenantApi.delete(TENANT_USUARIOS.byId(id))
}

export async function listModuloOptions(): Promise<ModuloOption[]> {
  const { data } = await tenantApi.get<ModuloOption[]>(TENANT_USUARIOS.modules)
  return data ?? []
}

export async function listRolOptions(): Promise<RolOption[]> {
  const { data } = await tenantApi.get<RolOption[]>(TENANT_USUARIOS.roles)
  return data ?? []
}

export async function checkUsernameAvailability(username: string): Promise<boolean> {
  const { data } = await tenantApi.get<{ available: boolean }>(TENANT_USUARIOS.checkUsername(username))
  return Boolean(data?.available)
}
