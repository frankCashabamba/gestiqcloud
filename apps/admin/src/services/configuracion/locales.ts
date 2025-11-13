import api from '../../shared/api/client'
import { ADMIN_CONFIG } from '@shared/endpoints'

export type Locale = { code: string; name: string; active?: boolean }

export async function listLocales(): Promise<Locale[]> {
  const { data } = await api.get<Locale[]>(`${ADMIN_CONFIG.locales.base}`)
  return data || []
}

export async function getLocale(code: string): Promise<Locale> {
  const { data } = await api.get<Locale>(ADMIN_CONFIG.locales.byId(code))
  return data
}

export async function createLocale(payload: Locale): Promise<Locale> {
  const { data } = await api.post<Locale>(`${ADMIN_CONFIG.locales.base}`, payload as any)
  return data
}

export async function updateLocale(code: string, payload: Partial<Locale>): Promise<Locale> {
  const { data } = await api.put<Locale>(ADMIN_CONFIG.locales.byId(code), payload as any)
  return data
}

export async function removeLocale(code: string): Promise<void> {
  await api.delete(ADMIN_CONFIG.locales.byId(code))
}
