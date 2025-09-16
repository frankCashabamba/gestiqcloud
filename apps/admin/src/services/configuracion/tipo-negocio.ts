import api from '../../shared/api/client'
import { ADMIN_CONFIG } from '@shared/endpoints'

export type TipoNegocio = { id: number; nombre: string }

export async function listTipoNegocio(): Promise<TipoNegocio[]> {
  const { data } = await api.get<TipoNegocio[]>(ADMIN_CONFIG.tipoNegocio.base)
  return data || []
}

export async function getTipoNegocio(id: number | string): Promise<TipoNegocio> {
  const { data } = await api.get<TipoNegocio>(ADMIN_CONFIG.tipoNegocio.byId(id))
  return data
}

export async function createTipoNegocio(payload: Omit<TipoNegocio, 'id'>): Promise<TipoNegocio> {
  const { data } = await api.post<TipoNegocio>(ADMIN_CONFIG.tipoNegocio.base, payload)
  return data
}

export async function updateTipoNegocio(id: number | string, payload: Omit<TipoNegocio, 'id'>): Promise<TipoNegocio> {
  const { data } = await api.put<TipoNegocio>(ADMIN_CONFIG.tipoNegocio.byId(id), payload)
  return data
}

export async function removeTipoNegocio(id: number | string): Promise<void> {
  await api.delete(ADMIN_CONFIG.tipoNegocio.byId(id))
}

