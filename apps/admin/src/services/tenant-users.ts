// src/services/tenant-users.ts

import api from '../shared/api/client'

export interface TenantUser {
  id: string
  email: string
  name: string
  apellidos?: string
  roles: string[]
  active: boolean
  ultima_conexion?: string
  created_at: string
}

export interface CreateUserPayload {
  email: string
  name: string
  apellidos?: string
  password: string
  roles: string[]
}

export interface UpdateUserPayload {
  name?: string
  apellidos?: string
  roles?: string[]
  active?: boolean
}

export interface UserActivity {
  id: string
  user_id: string
  action: string
  module: string
  ip_address?: string
  timestamp: string
  metadata?: any
}

export async function listTenantUsers(
  tenantId: string | number,
  params?: { search?: string; active?: boolean; page?: number; per_page?: number }
) {
  const { data } = await api.get(`/api/v1/admin/tenants/${tenantId}/users`, { params })
  return data
}

export async function createTenantUser(tenantId: string | number, payload: CreateUserPayload) {
  const { data } = await api.post(`/api/v1/admin/tenants/${tenantId}/users`, payload)
  return data
}

export async function updateTenantUser(
  tenantId: string | number,
  userId: string,
  payload: UpdateUserPayload
) {
  const { data } = await api.put(`/api/v1/admin/tenants/${tenantId}/users/${userId}`, payload)
  return data
}

export async function resetUserPassword(tenantId: string | number, userId: string) {
  const { data } = await api.post(`/api/v1/admin/tenants/${tenantId}/users/${userId}/reset-password`)
  return data
}

export async function toggleUserActive(
  tenantId: string | number,
  userId: string,
  active: boolean
) {
  const { data } = await api.patch(`/api/v1/admin/tenants/${tenantId}/users/${userId}`, { active })
  return data
}

export async function deleteUser(tenantId: string | number, userId: string) {
  const { data } = await api.delete(`/api/v1/admin/tenants/${tenantId}/users/${userId}`)
  return data
}

export async function getUserActivity(userId: string, limit: number = 20) {
  const { data } = await api.get(`/api/v1/admin/users/${userId}/activity`, {
    params: { limit }
  })
  return data
}
