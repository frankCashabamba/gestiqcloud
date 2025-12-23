import api from '../shared/api/client'
import { ADMIN_USUARIOS } from '@shared/endpoints'

export type AdminUsuario = {
  id: string | number
  name?: string | null
  email?: string | null
  is_company_admin?: boolean
  active?: boolean
}

export async function listUsuarios(): Promise<AdminUsuario[]> {
  const { data } = await api.get<AdminUsuario[]>(ADMIN_USUARIOS.base)
  return data || []
}

export async function reenviarReset(id: number | string): Promise<void> {
  await api.post(ADMIN_USUARIOS.reenviarReset(String(id)))
}

export async function activarUsuario(id: number | string): Promise<void> {
  await api.post(ADMIN_USUARIOS.activar(String(id)))
}

export async function desactivarUsuario(id: number | string): Promise<void> {
  await api.post(ADMIN_USUARIOS.desactivar(String(id)))
}

export async function desactivarEmpresa(id: number | string): Promise<void> {
  await api.post(ADMIN_USUARIOS.desactivarEmpresa(String(id)))
}

export async function asignarNuevoAdmin(id: number | string, payload: { email?: string; usuario_id?: number | string }) {
  await api.post(ADMIN_USUARIOS.asignarNuevoAdmin(String(id)), payload)
}

export async function setPasswordDirect(id: number | string, password: string): Promise<void> {
  await api.post(ADMIN_USUARIOS.setPassword(String(id)), { password })
}
