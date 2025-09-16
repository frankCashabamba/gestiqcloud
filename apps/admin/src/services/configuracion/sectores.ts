import api from '../../shared/api/client'
import { ADMIN_CONFIG } from '@shared/endpoints'

export type TipoEmpresa = { id: number; nombre: string }
export type TipoNegocio = { id: number; nombre: string }

export type Sector = {
  id: number
  nombre: string
  tipo_empresa_id: number
  tipo_negocio_id: number
  config_json: Record<string, any>
}

export async function listSectores(): Promise<Sector[]> {
  const { data } = await api.get<Sector[]>(ADMIN_CONFIG.sectores.base)
  return data || []
}

export async function getSector(id: number | string): Promise<Sector> {
  const { data } = await api.get<Sector>(ADMIN_CONFIG.sectores.byId(id))
  return data
}

export async function createSector(payload: Omit<Sector, 'id'>): Promise<Sector> {
  const { data } = await api.post<Sector>(ADMIN_CONFIG.sectores.base, payload)
  return data
}

export async function updateSector(id: number | string, payload: Omit<Sector, 'id'>): Promise<Sector> {
  const { data } = await api.put<Sector>(ADMIN_CONFIG.sectores.byId(id), payload)
  return data
}

export async function removeSector(id: number | string): Promise<void> {
  await api.delete(ADMIN_CONFIG.sectores.byId(id))
}

export async function listTipoEmpresa(): Promise<TipoEmpresa[]> {
  const { data } = await api.get<TipoEmpresa[]>(ADMIN_CONFIG.tipoEmpresa.base)
  return data || []
}

export async function listTipoNegocio(): Promise<TipoNegocio[]> {
  const { data } = await api.get<TipoNegocio[]>(ADMIN_CONFIG.tipoNegocio.base)
  return data || []
}

