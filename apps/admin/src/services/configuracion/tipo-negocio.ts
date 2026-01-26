import api from '../../shared/api/client'
import { ADMIN_CONFIG } from '@shared/endpoints'

export type TipoNegocio = {
  id: string
  name: string
  description?: string | null
  active?: boolean
}

type TipoNegocioPayload = Omit<TipoNegocio, 'id'>

export async function listTipoNegocio(): Promise<TipoNegocio[]> {
  const { data } = await api.get<TipoNegocio[]>(ADMIN_CONFIG.businessType.base)
  return data || []
}

export async function getTipoNegocio(id: number | string): Promise<TipoNegocio> {
  const { data } = await api.get<TipoNegocio>(ADMIN_CONFIG.businessType.byId(id))
  return data
}

export async function createTipoNegocio(payload: TipoNegocioPayload): Promise<TipoNegocio> {
  const { data } = await api.post<TipoNegocio>(ADMIN_CONFIG.businessType.base, payload)
  return data
}

export async function updateTipoNegocio(id: number | string, payload: TipoNegocioPayload): Promise<TipoNegocio> {
  const { data } = await api.put<TipoNegocio>(ADMIN_CONFIG.businessType.byId(id), payload)
  return data
}

export async function removeTipoNegocio(id: number | string): Promise<void> {
  await api.delete(ADMIN_CONFIG.businessType.byId(id))
}
