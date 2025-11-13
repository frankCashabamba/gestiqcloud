import api from '../../shared/api/client'
import { ADMIN_CONFIG } from '@shared/endpoints'

type MonedaAliases = {
  /**
   * Algunas API legacy siguen devolviendo estos nombres en inglés. Los marcamos como opcionales
   * para que el tipado admita ambos formatos sin romper el typecheck.
   */
  code?: string
  name?: string
  symbol?: string
  active?: boolean
}

export type Moneda = {
  id: number
  codigo: string
  nombre: string
  simbolo: string
  activo: boolean
} & MonedaAliases

type MonedaPayload = Pick<Moneda, 'codigo' | 'nombre' | 'simbolo' | 'activo'>

const normalizeMoneda = (input: Partial<Moneda>): Moneda => ({
  id: input.id ?? 0,
  codigo: input.codigo ?? input.code ?? '',
  nombre: input.nombre ?? input.name ?? '',
  simbolo: input.simbolo ?? input.symbol ?? '',
  activo: input.activo ?? input.active ?? true,
  code: input.code ?? input.codigo,
  name: input.name ?? input.nombre,
  symbol: input.symbol ?? input.simbolo,
  active: input.active ?? input.activo,
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

