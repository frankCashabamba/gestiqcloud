import api from '../../shared/api/client'

export async function getAllSettings() {
  const response = await api.get('/api/v1/settings')
  return response.data
}

export async function getModuleSettings(moduleKey: string) {
  const response = await api.get(`/api/v1/settings/${moduleKey}`)
  return response.data
}

export async function updateModuleSettings(moduleKey: string, data: any) {
  const response = await api.put(`/api/v1/settings/${moduleKey}`, data)
  return response.data
}

export async function enableModule(moduleKey: string) {
  const response = await api.post(`/api/v1/settings/${moduleKey}/enable`)
  return response.data
}

export async function disableModule(moduleKey: string) {
  const response = await api.post(`/api/v1/settings/${moduleKey}/disable`)
  return response.data
}

export async function listAvailableModules() {
  const response = await api.get('/api/v1/settings/modules')
  return response.data
}
