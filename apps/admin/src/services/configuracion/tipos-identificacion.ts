import { ADMIN_CONFIG } from '@shared/endpoints'

import api from '../../shared/api/client'

export type TipoIdentificacion = {
  id: string
  country_code: string
  code: string
  label: string
  active: boolean
}

type Payload = Omit<TipoIdentificacion, 'id'>

const normalize = (input: Partial<TipoIdentificacion>): TipoIdentificacion => ({
  id: input.id ?? '',
  country_code: input.country_code ?? '',
  code: input.code ?? '',
  label: input.label ?? '',
  active: input.active ?? true,
})

export async function listTiposIdentificacion(): Promise<TipoIdentificacion[]> {
  const { data } = await api.get<Partial<TipoIdentificacion>[]>(ADMIN_CONFIG.identificationTypes.base)
  return (data || []).map(normalize)
}

export async function getTipoIdentificacion(id: string): Promise<TipoIdentificacion> {
  try {
    const { data } = await api.get<Partial<TipoIdentificacion>>(ADMIN_CONFIG.identificationTypes.byId(id))
    return normalize(data || {})
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const list = await listTiposIdentificacion()
      const found = list.find((m) => m.id === id)
      if (found) return found
    }
    throw err
  }
}

export async function createTipoIdentificacion(payload: Payload): Promise<TipoIdentificacion> {
  const { data } = await api.post<Partial<TipoIdentificacion>>(ADMIN_CONFIG.identificationTypes.base, payload)
  return normalize(data || payload)
}

export async function updateTipoIdentificacion(id: string, payload: Payload): Promise<TipoIdentificacion> {
  const { data } = await api.put<Partial<TipoIdentificacion>>(ADMIN_CONFIG.identificationTypes.byId(id), payload)
  return normalize(data || payload)
}

export async function removeTipoIdentificacion(id: string): Promise<void> {
  await api.delete(ADMIN_CONFIG.identificationTypes.byId(id))
}
