import api from '../../shared/api/client'
import { SETTINGS_MODULES } from '@shared/endpoints'

export async function listAvailableModules() {
  const response = await api.get(SETTINGS_MODULES)
  return response.data
}
