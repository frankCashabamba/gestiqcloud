import api from '../../shared/api/client'
import { ADMIN_CONFIG } from '@shared/endpoints'

export type Idioma = {
  id: number
  codigo: string
  nombre: string
  activo: boolean
}

export async function listIdiomas(): Promise<Idioma[]> {
  const { data } = await api.get<Idioma[]>(`${ADMIN_CONFIG.idiomas.base}`)
  return data || []
}

export async function getIdioma(id: number | string): Promise<Idioma> {
  const { data } = await api.get<Idioma>(ADMIN_CONFIG.idiomas.byId(id))
  return data
}

export async function createIdioma(payload: Omit<Idioma, 'id'>): Promise<Idioma> {
  const { data } = await api.post<Idioma>(`${ADMIN_CONFIG.idiomas.base}`, payload)
  return data
}

export async function updateIdioma(id: number | string, payload: Omit<Idioma, 'id'>): Promise<Idioma> {
  const { data } = await api.put<Idioma>(ADMIN_CONFIG.idiomas.byId(id), payload)
  return data
}

export async function removeIdioma(id: number | string): Promise<void> {
  await api.delete(ADMIN_CONFIG.idiomas.byId(id))
}

