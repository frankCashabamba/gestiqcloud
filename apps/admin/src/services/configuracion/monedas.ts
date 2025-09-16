import api from '../../shared/api/client'
import { ADMIN_CONFIG } from '@shared/endpoints'

export type Moneda = {
  id: number
  codigo: string
  nombre: string
  simbolo: string
  activo: boolean
}

export async function listMonedas(): Promise<Moneda[]> {
  const { data } = await api.get<Moneda[]>(`${ADMIN_CONFIG.monedas.base}`)
  return data || []
}

export async function getMoneda(id: number | string): Promise<Moneda> {
  const { data } = await api.get<Moneda>(ADMIN_CONFIG.monedas.byId(id))
  return data
}

export async function createMoneda(payload: Omit<Moneda, 'id'>): Promise<Moneda> {
  const { data } = await api.post<Moneda>(`${ADMIN_CONFIG.monedas.base}`, payload)
  return data
}

export async function updateMoneda(id: number | string, payload: Omit<Moneda, 'id'>): Promise<Moneda> {
  const { data } = await api.put<Moneda>(ADMIN_CONFIG.monedas.byId(id), payload)
  return data
}

export async function removeMoneda(id: number | string): Promise<void> {
  await api.delete(ADMIN_CONFIG.monedas.byId(id))
}

