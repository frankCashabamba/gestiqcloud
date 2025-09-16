import api from '../../shared/api/client'
import { ADMIN_CONFIG } from '@shared/endpoints'

export type TipoEmpresa = { id: number; nombre: string }

export async function listTipoEmpresa(): Promise<TipoEmpresa[]> {
  const { data } = await api.get<TipoEmpresa[]>(ADMIN_CONFIG.tipoEmpresa.base)
  return data || []
}

export async function getTipoEmpresa(id: number | string): Promise<TipoEmpresa> {
  const { data } = await api.get<TipoEmpresa>(ADMIN_CONFIG.tipoEmpresa.byId(id))
  return data
}

export async function createTipoEmpresa(payload: Omit<TipoEmpresa, 'id'>): Promise<TipoEmpresa> {
  const { data } = await api.post<TipoEmpresa>(ADMIN_CONFIG.tipoEmpresa.base, payload)
  return data
}

export async function updateTipoEmpresa(id: number | string, payload: Omit<TipoEmpresa, 'id'>): Promise<TipoEmpresa> {
  const { data } = await api.put<TipoEmpresa>(ADMIN_CONFIG.tipoEmpresa.byId(id), payload)
  return data
}

export async function removeTipoEmpresa(id: number | string): Promise<void> {
  await api.delete(ADMIN_CONFIG.tipoEmpresa.byId(id))
}

