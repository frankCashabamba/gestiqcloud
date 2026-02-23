import api from '../../shared/api/client'
import { ADMIN_CONFIG } from '@shared/endpoints'

export type TipoImpuesto = {
  id: string
  country_code: string
  code: string
  name: string
  rate_default: number | null
  active: boolean
}

type TipoImpuestoPayload = Pick<TipoImpuesto, 'country_code' | 'code' | 'name' | 'rate_default' | 'active'>

const normalizeTipoImpuesto = (input: Partial<TipoImpuesto>): TipoImpuesto => ({
  id: input.id ?? '',
  country_code: input.country_code ?? '',
  code: input.code ?? '',
  name: input.name ?? '',
  rate_default: input.rate_default ?? null,
  active: input.active ?? true,
})

const buildPayload = (payload: TipoImpuestoPayload) => ({
  country_code: payload.country_code,
  code: payload.code,
  name: payload.name,
  rate_default: payload.rate_default,
  active: payload.active,
})

export async function listTiposImpuesto(): Promise<TipoImpuesto[]> {
  const { data } = await api.get<Partial<TipoImpuesto>[]>(`${ADMIN_CONFIG.taxTypes.base}`)
  return (data || []).map(normalizeTipoImpuesto)
}

export async function getTipoImpuesto(id: number | string): Promise<TipoImpuesto> {
  try {
    const { data } = await api.get<Partial<TipoImpuesto>>(ADMIN_CONFIG.taxTypes.byId(id))
    return normalizeTipoImpuesto(data || {})
  } catch (err: any) {
    const status = err?.response?.status
    if (status === 404 || status === 405) {
      const list = await listTiposImpuesto()
      const found = list.find((m) => String(m.id) === String(id))
      if (found) return found
    }
    throw err
  }
}

export async function createTipoImpuesto(payload: TipoImpuestoPayload): Promise<TipoImpuesto> {
  const { data } = await api.post<Partial<TipoImpuesto>>(`${ADMIN_CONFIG.taxTypes.base}`, buildPayload(payload))
  return normalizeTipoImpuesto(data || payload)
}

export async function updateTipoImpuesto(id: number | string, payload: TipoImpuestoPayload): Promise<TipoImpuesto> {
  const { data } = await api.put<Partial<TipoImpuesto>>(ADMIN_CONFIG.taxTypes.byId(id), buildPayload(payload))
  return normalizeTipoImpuesto(data || payload)
}

export async function removeTipoImpuesto(id: number | string): Promise<void> {
  await api.delete(ADMIN_CONFIG.taxTypes.byId(id))
}
