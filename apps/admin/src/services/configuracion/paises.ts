import api from '../../shared/api/client'
import { ADMIN_CONFIG } from '@shared/endpoints'

export type Pais = {
  id: number
  code: string
  name: string
  active: boolean
}

export async function listPaises(): Promise<Pais[]> {
  const { data } = await api.get<Pais[]>(`${ADMIN_CONFIG.paises.base}`)
  return data || []
}

export async function getPais(id: number | string): Promise<Pais> {
  const { data } = await api.get<Pais>(ADMIN_CONFIG.paises.byId(id))
  return data
}

export async function createPais(payload: Omit<Pais, 'id'>): Promise<Pais> {
  const { data } = await api.post<Pais>(`${ADMIN_CONFIG.paises.base}`, payload)
  return data
}

export async function updatePais(id: number | string, payload: Omit<Pais, 'id'>): Promise<Pais> {
  const { data } = await api.put<Pais>(ADMIN_CONFIG.paises.byId(id), payload)
  return data
}

export async function removePais(id: number | string): Promise<void> {
  await api.delete(ADMIN_CONFIG.paises.byId(id))
}

