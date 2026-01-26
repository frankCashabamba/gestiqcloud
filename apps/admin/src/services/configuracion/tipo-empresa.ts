import api from '../../shared/api/client'
import { ADMIN_CONFIG } from '@shared/endpoints'

export type TipoEmpresa = {
  id: string
  name: string
  description?: string | null
  active?: boolean
}

type TipoEmpresaPayload = Omit<TipoEmpresa, 'id'>

export async function listTipoEmpresa(): Promise<TipoEmpresa[]> {
  const { data } = await api.get<TipoEmpresa[]>(ADMIN_CONFIG.businessCategory.base)
  return data || []
}

export async function getTipoEmpresa(id: number | string): Promise<TipoEmpresa> {
  const { data } = await api.get<TipoEmpresa>(ADMIN_CONFIG.businessCategory.byId(id))
  return data
}

export async function createTipoEmpresa(payload: TipoEmpresaPayload): Promise<TipoEmpresa> {
  const { data } = await api.post<TipoEmpresa>(ADMIN_CONFIG.businessCategory.base, payload)
  return data
}

export async function updateTipoEmpresa(id: number | string, payload: TipoEmpresaPayload): Promise<TipoEmpresa> {
  const { data } = await api.put<TipoEmpresa>(ADMIN_CONFIG.businessCategory.byId(id), payload)
  return data
}

export async function removeTipoEmpresa(id: number | string): Promise<void> {
  await api.delete(ADMIN_CONFIG.businessCategory.byId(id))
}
