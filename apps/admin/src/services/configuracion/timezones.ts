import api from '../../shared/api/client'
import { ADMIN_CONFIG } from '@shared/endpoints'

export type Timezone = { name: string; display_name: string; offset_minutes?: number | null; active?: boolean }

export async function listTimezones(): Promise<Timezone[]> {
  const { data } = await api.get<Timezone[]>(`${ADMIN_CONFIG.timezones.base}`)
  return data || []
}

export async function getTimezone(name: string): Promise<Timezone> {
  const { data } = await api.get<Timezone>(ADMIN_CONFIG.timezones.byId(name))
  return data
}

export async function createTimezone(payload: Timezone): Promise<Timezone> {
  const { data } = await api.post<Timezone>(`${ADMIN_CONFIG.timezones.base}`, payload as any)
  return data
}

export async function updateTimezone(name: string, payload: Partial<Timezone>): Promise<Timezone> {
  const { data } = await api.put<Timezone>(ADMIN_CONFIG.timezones.byId(name), payload as any)
  return data
}

export async function removeTimezone(name: string): Promise<void> {
  await api.delete(ADMIN_CONFIG.timezones.byId(name))
}
