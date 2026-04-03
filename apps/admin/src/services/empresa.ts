// src/services/empresa.ts

import { createEmpresaService } from '@shared/domain/empresa'
import { ADMIN_COMPANIES } from '@shared/endpoints'

import api from '../shared/api/client'

const svc = createEmpresaService(api, { base: ADMIN_COMPANIES.base })

// Re-export solo los usados actualmente (alta completa usa createFull)
export const { getEmpresas, updateEmpresa } = svc as any

export async function deleteEmpresa(id: number | string): Promise<any> {
  const tenantId = String(id).trim()
  const { data } = await api.delete(`${ADMIN_COMPANIES.byId(tenantId)}?confirm_tenant_id=${encodeURIComponent(tenantId)}`)
  return data
}

export async function createEmpresaFull(payload: any): Promise<{ msg: string; id?: string | number }> {
  const { data } = await api.post(ADMIN_COMPANIES.createFull, payload)
  return data
}

export async function getEmpresa(id: number | string): Promise<any> {
  const { data } = await api.get(ADMIN_COMPANIES.byId(id))
  return data
}

export async function deleteAllEmpresas(): Promise<any> {
  const { data } = await api.post(ADMIN_COMPANIES.deleteAll, {
    confirm: 'DELETE_ALL_COMPANIES',
  })
  return data
}

export async function purgeOrphanCompanyData(): Promise<any> {
  const { data } = await api.post(ADMIN_COMPANIES.purgeOrphans)
  return data
}
