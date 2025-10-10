import api from '../shared/api/client'
import { ADMIN_USUARIOS } from '@shared/endpoints'

export type AdminUsuario = {
  id: number | string
  nombre?: string
  email?: string
  es_admin?: boolean
  rol?: string
  activo?: boolean
}

export async function listUsuarios(): Promise<AdminUsuario[]> {
  const { data } = await api.get<AdminUsuario[]>(ADMIN_USUARIOS.base)
  return data || []
}

export async function reenviarReset(id: number | string): Promise<void> {
  await api.post(ADMIN_USUARIOS.reenviarReset(id))
}

export async function activarUsuario(id: number | string): Promise<void> {
  await api.post(ADMIN_USUARIOS.activar(id))
}

export async function desactivarUsuario(id: number | string): Promise<void> {
  await api.post(ADMIN_USUARIOS.desactivar(id))
}

export async function desactivarEmpresa(id: number | string): Promise<void> {
  await api.post(ADMIN_USUARIOS.desactivarEmpresa(id))
}

export async function asignarNuevoAdmin(id: number | string, payload: { email?: string; usuario_id?: number | string }) {
  await api.post(ADMIN_USUARIOS.asignarNuevoAdmin(id), payload)
}

export async function setPasswordDirect(id: number | string, password: string): Promise<void> {
  await api.post(ADMIN_USUARIOS.setPassword(id), { password })
}
