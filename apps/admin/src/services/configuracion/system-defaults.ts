import { ADMIN_CONFIG } from '@shared/endpoints'

import api from '../../shared/api/client'

export type SystemDefault = {
  key: string
  category: string
  value_text: string | null
  description: string | null
  value_type: string
  updated_at: string | null
}

export async function listSystemDefaults(): Promise<SystemDefault[]> {
  const { data } = await api.get<SystemDefault[]>(ADMIN_CONFIG.systemDefaults.base)
  return data || []
}

export async function updateSystemDefault(key: string, value: string): Promise<SystemDefault> {
  const { data } = await api.put<SystemDefault>(ADMIN_CONFIG.systemDefaults.byKey(key), { value })
  return data
}
