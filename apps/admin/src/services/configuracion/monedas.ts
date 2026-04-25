import { ADMIN_CONFIG } from '@shared/endpoints'

import api from '../../shared/api/client'

export type Moneda = {
  id: number
  code: string
  name: string
  symbol: string
  active: boolean
}

type MonedaPayload = Pick<Moneda, 'code' | 'name' | 'symbol' | 'active'>

export async function listMonedas(): Promise<Moneda[]> {
  const { data } = await api.get<Moneda[]>(`${ADMIN_CONFIG.currencies.base}`)
  return data || []
}

export async function getMoneda(id: number | string): Promise<Moneda> {
  try {
    const { data } = await api.get<Moneda>(ADMIN_CONFIG.currencies.byId(id))
    return data
  } catch (err: any) {
    const status = err?.response?.status
    if (status === 404 || status === 405) {
      const list = await listMonedas()
      const found = list.find((m) => String(m.id) === String(id))
      if (found) return found
    }
    throw err
  }
}

export async function createMoneda(payload: MonedaPayload): Promise<Moneda> {
  const { data } = await api.post<Moneda>(`${ADMIN_CONFIG.currencies.base}`, payload)
  return data
}

export async function updateMoneda(id: number | string, payload: MonedaPayload): Promise<Moneda> {
  const { data } = await api.put<Moneda>(ADMIN_CONFIG.currencies.byId(id), payload)
  return data
}

export async function removeMoneda(id: number | string): Promise<void> {
  await api.delete(ADMIN_CONFIG.currencies.byId(id))
}
