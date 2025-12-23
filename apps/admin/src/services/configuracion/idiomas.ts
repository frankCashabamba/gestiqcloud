import api from '../../shared/api/client'
import { ADMIN_CONFIG } from '@shared/endpoints'

export type Idioma = {
  id: number | string
  code: string
  name: string
  active: boolean
}

const normalize = (raw: any): Idioma => ({
  id: raw?.id,
  code: raw?.code ?? raw?.codigo ?? '',
  name: raw?.name ?? raw?.nombre ?? '',
  active: raw?.active ?? raw?.activo ?? false,
})

const toPayload = (payload: Omit<Idioma, 'id'>) => ({
  code: payload.code,
  name: payload.name,
  active: payload.active,
})

export async function listIdiomas(): Promise<Idioma[]> {
  const { data } = await api.get<Idioma[]>(`${ADMIN_CONFIG.idiomas.base}`)
  return (data || []).map(normalize)
}

export async function getIdioma(id: number | string): Promise<Idioma> {
  const { data } = await api.get<Idioma>(ADMIN_CONFIG.idiomas.byId(id))
  return normalize(data)
}

export async function createIdioma(payload: Omit<Idioma, 'id'>): Promise<Idioma> {
  const { data } = await api.post<Idioma>(`${ADMIN_CONFIG.idiomas.base}`, toPayload(payload))
  return normalize(data)
}

export async function updateIdioma(id: number | string, payload: Omit<Idioma, 'id'>): Promise<Idioma> {
  const { data } = await api.put<Idioma>(ADMIN_CONFIG.idiomas.byId(id), toPayload(payload))
  return normalize(data)
}

export async function removeIdioma(id: number | string): Promise<void> {
  await api.delete(ADMIN_CONFIG.idiomas.byId(id))
}
