import api from '../../shared/api/client'
import { ADMIN_CONFIG } from '@shared/endpoints'

export type Moneda = {
  id: number
  codigo: string
  nombre: string
  simbolo: string
  activo: boolean
}

type MonedaPayload = Pick<Moneda, 'codigo' | 'nombre' | 'simbolo' | 'activo'>

const normalizeMoneda = (input: Partial<Moneda>): Moneda => ({
  id: input.id ?? 0,
  codigo: input.codigo ?? '',
  nombre: input.nombre ?? '',
  simbolo: input.simbolo ?? '',
  activo: input.activo ?? true,
})

const buildPayload = (payload: MonedaPayload) => ({
  codigo: payload.codigo,
  nombre: payload.nombre,
  simbolo: payload.simbolo,
  activo: payload.activo,
})

export async function listMonedas(): Promise<Moneda[]> {
  const { data } = await api.get<Partial<Moneda>[]>(`${ADMIN_CONFIG.monedas.base}`)
  return (data || []).map(normalizeMoneda)
}

export async function getMoneda(id: number | string): Promise<Moneda> {
  const { data } = await api.get<Partial<Moneda>>(ADMIN_CONFIG.monedas.byId(id))
  return normalizeMoneda(data || {})
}

export async function createMoneda(payload: MonedaPayload): Promise<Moneda> {
  const { data } = await api.post<Partial<Moneda>>(`${ADMIN_CONFIG.monedas.base}`, buildPayload(payload))
  return normalizeMoneda(data || payload)
}

export async function updateMoneda(id: number | string, payload: MonedaPayload): Promise<Moneda> {
  const { data } = await api.put<Partial<Moneda>>(ADMIN_CONFIG.monedas.byId(id), buildPayload(payload))
  return normalizeMoneda(data || payload)
}

export async function removeMoneda(id: number | string): Promise<void> {
  await api.delete(ADMIN_CONFIG.monedas.byId(id))
}
