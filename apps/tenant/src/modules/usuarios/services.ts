import tenantApi from '../../shared/api/client'
import { TENANT_USUARIOS, TENANT_ROLES } from '@shared/endpoints'
import type {
  Usuario,
  UsuarioCreatePayload,
  UsuarioUpdatePayload,
  ModuloOption,
  RolOption,
  Rol,
} from './types'

// Payloads para roles
export type RolCreatePayload = {
  name: string
  description?: string
  permissions: Record<string, boolean>
}

export type RolUpdatePayload = Partial<RolCreatePayload>

export type GlobalPermission = {
  id: number
  key: string
  module?: string | null
  description?: string | null
}

type PermissionsCache = {
  data: GlobalPermission[]
  ts: number
}

let permissionsCache: PermissionsCache | null = null
let permissionsPromise: Promise<GlobalPermission[]> | null = null
const PERMISSIONS_TTL_MS = 5 * 60 * 1000

export async function listUsuarios(): Promise<Usuario[]> {
  const { data } = await tenantApi.get<Usuario[]>(TENANT_USUARIOS.base)
  return Array.isArray(data) ? data : []
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

export async function setUsuarioPassword(id: number | string, password: string): Promise<void> {
  await tenantApi.post(TENANT_USUARIOS.setPassword(id), { password })
}

// Gestión de Roles
export async function listRoles(): Promise<Rol[]> {
  const { data } = await tenantApi.get<Rol[]>(TENANT_ROLES.base)
  return Array.isArray(data) ? data : []
}

export async function getRol(id: number | string): Promise<Rol> {
  const { data } = await tenantApi.get<Rol>(TENANT_ROLES.byId(id))
  return data
}

export async function createRol(payload: RolCreatePayload): Promise<Rol> {
  const { data } = await tenantApi.post<Rol>(TENANT_ROLES.base, payload)
  return data
}

export async function updateRol(id: number | string, payload: RolUpdatePayload): Promise<Rol> {
  const { data } = await tenantApi.patch<Rol>(TENANT_ROLES.byId(id), payload)
  return data
}

export async function deleteRol(id: number | string): Promise<void> {
  await tenantApi.delete(TENANT_ROLES.byId(id))
}

export async function listGlobalPermissions(force = false): Promise<GlobalPermission[]> {
  const now = Date.now()
  if (!force && permissionsCache && now - permissionsCache.ts < PERMISSIONS_TTL_MS) {
    return permissionsCache.data
  }
  if (!force && permissionsPromise) {
    return permissionsPromise
  }
  permissionsPromise = (async () => {
    const { data } = await tenantApi.get<GlobalPermission[]>('/api/v1/roles-base/global-permissions')
    const safe = Array.isArray(data) ? data : []
    permissionsCache = { data: safe, ts: Date.now() }
    return safe
  })()
  try {
    return await permissionsPromise
  } finally {
    permissionsPromise = null
  }
}
