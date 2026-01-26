import api from '../../shared/api/client'
import { ADMIN_CONFIG } from '@shared/endpoints'

export type Moneda = {
  id: number
  code: string
  name: string
  symbol: string
  active: boolean
}

type MonedaPayload = Pick<Moneda, 'code' | 'name' | 'symbol' | 'active'>

const normalizeMoneda = (input: Partial<Moneda>): Moneda => ({
  id: input.id ?? 0,
  code: input.code ?? (input as any).codigo ?? '',
  name: input.name ?? (input as any).nombre ?? '',
  symbol: input.symbol ?? (input as any).simbolo ?? '',
  active: input.active ?? (input as any).activo ?? true,
})

const buildPayload = (payload: MonedaPayload) => ({
  code: payload.code,
  name: payload.name,
  symbol: payload.symbol,
  active: payload.active,
})

export async function listMonedas(): Promise<Moneda[]> {
  const { data } = await api.get<Partial<Moneda>[]>(`${ADMIN_CONFIG.currencies.base}`)
  return (data || []).map(normalizeMoneda)
}

export async function getMoneda(id: number | string): Promise<Moneda> {
  const { data } = await api.get<Partial<Moneda>>(ADMIN_CONFIG.currencies.byId(id))
  return normalizeMoneda(data || {})
}

export async function createMoneda(payload: MonedaPayload): Promise<Moneda> {
  const { data } = await api.post<Partial<Moneda>>(`${ADMIN_CONFIG.currencies.base}`, buildPayload(payload))
  return normalizeMoneda(data || payload)
}

export async function updateMoneda(id: number | string, payload: MonedaPayload): Promise<Moneda> {
  const { data } = await api.put<Partial<Moneda>>(ADMIN_CONFIG.currencies.byId(id), buildPayload(payload))
  return normalizeMoneda(data || payload)
}

export async function removeMoneda(id: number | string): Promise<void> {
  await api.delete(ADMIN_CONFIG.currencies.byId(id))
}
