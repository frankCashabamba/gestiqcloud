import api from '../../shared/api/client'
import { ADMIN_CONFIG } from '@shared/endpoints'

export type UnidadMedida = {
  id: number
  code: string
  name: string
  abbreviation: string
  active: boolean
}

type UnidadMedidaPayload = Pick<UnidadMedida, 'code' | 'name' | 'abbreviation' | 'active'>

const normalizeUnidadMedida = (input: Partial<UnidadMedida>): UnidadMedida => ({
  id: input.id ?? 0,
  code: input.code ?? '',
  name: input.name ?? '',
  abbreviation: input.abbreviation ?? '',
  active: input.active ?? true,
})

const buildPayload = (payload: UnidadMedidaPayload) => ({
  code: payload.code,
  name: payload.name,
  abbreviation: payload.abbreviation,
  active: payload.active,
})

export async function listUnidades(): Promise<UnidadMedida[]> {
  const { data } = await api.get<Partial<UnidadMedida>[]>(`${ADMIN_CONFIG.units.base}`)
  return (data || []).map(normalizeUnidadMedida)
}

export async function getUnidad(id: number | string): Promise<UnidadMedida> {
  try {
    const { data } = await api.get<Partial<UnidadMedida>>(ADMIN_CONFIG.units.byId(id))
    return normalizeUnidadMedida(data || {})
  } catch (err: any) {
    const status = err?.response?.status
    if (status === 404 || status === 405) {
      const list = await listUnidades()
      const found = list.find((m) => String(m.id) === String(id))
      if (found) return found
    }
    throw err
  }
}

export async function createUnidad(payload: UnidadMedidaPayload): Promise<UnidadMedida> {
  const { data } = await api.post<Partial<UnidadMedida>>(`${ADMIN_CONFIG.units.base}`, buildPayload(payload))
  return normalizeUnidadMedida(data || payload)
}

export async function updateUnidad(id: number | string, payload: UnidadMedidaPayload): Promise<UnidadMedida> {
  const { data } = await api.put<Partial<UnidadMedida>>(ADMIN_CONFIG.units.byId(id), buildPayload(payload))
  return normalizeUnidadMedida(data || payload)
}

export async function removeUnidad(id: number | string): Promise<void> {
  await api.delete(ADMIN_CONFIG.units.byId(id))
}
