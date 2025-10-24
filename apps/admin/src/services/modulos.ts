import api from '../shared/api/client'
import { ADMIN_MODULOS, ADMIN_MODULOS_EMPRESA } from '@shared/endpoints'

export type Modulo = {
  id: number
  nombre: string
  url?: string
  plantilla_inicial?: string
  icono?: string
  activo?: boolean
  categoria?: string | null
  descripcion?: string | null
}

export async function listModulos(): Promise<Modulo[]> {
  const { data } = await api.get<Modulo[]>(ADMIN_MODULOS.base)
  return data || []
}

export async function getModulo(id: number | string): Promise<Modulo> {
  const { data } = await api.get<Modulo>(ADMIN_MODULOS.byId(id))
  return data
}

export async function createModulo(payload: Partial<Modulo>): Promise<Modulo> {
  const { data } = await api.post<Modulo>(ADMIN_MODULOS.base, payload)
  return data
}

export async function updateModulo(id: number | string, payload: Partial<Modulo>): Promise<Modulo> {
  const { data } = await api.put<Modulo>(ADMIN_MODULOS.byId(id), payload)
  return data
}

export async function removeModulo(id: number | string): Promise<void> {
  await api.delete(ADMIN_MODULOS.byId(id))
}

export async function toggleModulo(id: number | string, activar: boolean): Promise<Modulo> {
  const endpoint = activar ? ADMIN_MODULOS.activar(id) : ADMIN_MODULOS.desactivar(id)
  const { data } = await api.post<Modulo>(endpoint)
  return data
}

export type RegistrarRespuesta = {
  registrados: string[]
  ya_existentes?: string[]
  ignorados?: string[]
}

export async function registrarModulosFS(): Promise<RegistrarRespuesta> {
  const { data } = await api.post<RegistrarRespuesta>(ADMIN_MODULOS.registrar)
  return data
}

// ---- Empresa <-> Módulos ----
export type EmpresaModulo = {
  id: number
  empresa_id: number
  empresa_slug?: string
  activo: boolean
  fecha_activacion?: string
  fecha_expiracion?: string | null
  modulo_id: number
  modulo: Modulo
}

export async function listModulosPublicos(): Promise<Modulo[]> {
  const { data } = await api.get<Modulo[]>(ADMIN_MODULOS.publicos)
  return data || []
}

export async function listEmpresaModulos(empresaId: number | string): Promise<EmpresaModulo[]> {
  const { data } = await api.get<EmpresaModulo[]>(ADMIN_MODULOS_EMPRESA.base(empresaId))
  return data || []
}

export async function upsertEmpresaModulo(empresaId: number | string, moduloId: number, payload?: { activo?: boolean; fecha_expiracion?: string | null; plantilla_inicial?: string | null }) {
  const body = { modulo_id: moduloId, ...(payload || {}) }
  const { data } = await api.post(ADMIN_MODULOS_EMPRESA.upsert(empresaId), body)
  return data
}

export async function removeEmpresaModulo(empresaId: number | string, moduloId: number | string): Promise<void> {
  await api.delete(ADMIN_MODULOS_EMPRESA.remove(empresaId, moduloId))
}
