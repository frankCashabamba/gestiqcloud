// src/services/company-users.ts

import api from '../shared/api/client'

export interface CompanyUser {
  id: string
  email: string
  name: string
  lastName?: string
  roles: string[]
  active: boolean
  lastLogin?: string
  createdAt: string
}

export interface CreateUserPayload {
  email: string
  name: string
  lastName?: string
  password: string
  roles: string[]
}

export interface UpdateUserPayload {
  name?: string
  lastName?: string
  roles?: string[]
  active?: boolean
}

export interface UserActivity {
  id: string
  userId: string
  action: string
  module: string
  ipAddress?: string
  timestamp: string
  metadata?: any
}

function normalizeUser(raw: any): CompanyUser {
  return {
    id: String(raw?.id || ''),
    email: String(raw?.email || ''),
    name: String(raw?.name || ''),
    lastName: raw?.lastName ?? raw?.apellidos ?? undefined,
    roles: Array.isArray(raw?.roles) ? raw.roles.map(String) : [],
    active: Boolean(raw?.active),
    lastLogin: raw?.lastLogin ?? raw?.ultima_conexion ?? undefined,
    createdAt: String(raw?.createdAt ?? raw?.created_at ?? ''),
  }
}

function toApiCreateUserPayload(payload: CreateUserPayload) {
  return {
    email: payload.email,
    name: payload.name,
    apellidos: payload.lastName,
    password: payload.password,
    roles: payload.roles,
  }
}

function toApiUpdateUserPayload(payload: UpdateUserPayload) {
  return {
    name: payload.name,
    apellidos: payload.lastName,
    roles: payload.roles,
    active: payload.active,
  }
}

function normalizeActivity(raw: any): UserActivity {
  return {
    id: String(raw?.id || ''),
    userId: String(raw?.userId ?? raw?.user_id ?? ''),
    action: String(raw?.action || ''),
    module: String(raw?.module || ''),
    ipAddress: raw?.ipAddress ?? raw?.ip_address ?? undefined,
    timestamp: String(raw?.timestamp || ''),
    metadata: raw?.metadata,
  }
}

export async function listCompanyUsers(
  tenantId: string | number,
  params?: { search?: string; active?: boolean; page?: number; per_page?: number }
) {
  const { data } = await api.get(`/api/v1/admin/tenants/${tenantId}/users`, { params })
  return Array.isArray(data) ? data.map(normalizeUser) : []
}

export async function createCompanyUser(tenantId: string | number, payload: CreateUserPayload) {
  const { data } = await api.post(`/api/v1/admin/tenants/${tenantId}/users`, toApiCreateUserPayload(payload))
  return normalizeUser(data)
}

export async function updateCompanyUser(
  tenantId: string | number,
  userId: string,
  payload: UpdateUserPayload
) {
  const { data } = await api.put(`/api/v1/admin/tenants/${tenantId}/users/${userId}`, toApiUpdateUserPayload(payload))
  return normalizeUser(data)
}

export async function resetUserPassword(tenantId: string | number, userId: string) {
  const { data } = await api.post(`/api/v1/admin/tenants/${tenantId}/users/${userId}/reset-password`)
  return normalizeUser(data)
}

export async function toggleUserActive(
  tenantId: string | number,
  userId: string,
  active: boolean
) {
  const { data } = await api.patch(`/api/v1/admin/tenants/${tenantId}/users/${userId}`, { active })
  return normalizeUser(data)
}

export async function deleteUser(tenantId: string | number, userId: string) {
  const { data } = await api.delete(`/api/v1/admin/tenants/${tenantId}/users/${userId}`)
  return data
}

export async function getUserActivity(userId: string, limit: number = 20) {
  const { data } = await api.get(`/api/v1/admin/users/${userId}/activity`, {
    params: { limit }
  })
  return Array.isArray(data) ? data.map(normalizeActivity) : data
}
