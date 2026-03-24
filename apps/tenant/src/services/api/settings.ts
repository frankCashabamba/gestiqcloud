import api from '../../shared/api/client'

export async function listAvailableModules() {
  const response = await api.get('/api/v1/settings/modules')
  return response.data
}
