import api from '../../shared/api/client'

export type GlobalPermission = {
  id: number | string
  key: string
  module?: string | null
  description?: string | null
}

const normalize = (raw: any): GlobalPermission => ({
  id: raw?.id,
  key: raw?.key ?? '',
  module: raw?.module ?? null,
  description: raw?.description ?? null,
})

export async function listPermisos(): Promise<GlobalPermission[]> {
  const { data } = await api.get<GlobalPermission[]>('/v1/roles-base/global-permissions')
  return (data || []).map(normalize)
}

export async function getPermiso(id: number | string): Promise<GlobalPermission> {
  const { data } = await api.get<GlobalPermission>(`/v1/roles-base/global-permissions/${id}`)
  return normalize(data)
}

export async function createPermiso(payload: Omit<GlobalPermission, 'id'>): Promise<GlobalPermission> {
  const { data } = await api.post<GlobalPermission>('/v1/roles-base/global-permissions', payload)
  return normalize(data)
}

export async function updatePermiso(
  id: number | string,
  payload: Omit<GlobalPermission, 'id'>
): Promise<GlobalPermission> {
  const { data } = await api.put<GlobalPermission>(`/v1/roles-base/global-permissions/${id}`, payload)
  return normalize(data)
}

export async function removePermiso(id: number | string): Promise<void> {
  await api.delete(`/v1/roles-base/global-permissions/${id}`)
}
