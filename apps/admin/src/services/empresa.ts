// src/services/empresa.ts

import api from '../shared/api/client'
import { ADMIN_COMPANIES } from '@shared/endpoints'
import { createEmpresaService } from '@shared/domain/empresa'

const svc = createEmpresaService(api, { base: ADMIN_COMPANIES.base })

// Re-export solo los usados actualmente (alta completa usa createFull)
export const { getEmpresas, updateEmpresa, deleteEmpresa } = svc as any

export async function createEmpresaFull(payload: any): Promise<{ msg: string; id?: number }> {
  const { data } = await api.post(ADMIN_COMPANIES.createFull, payload)
  return data
}

export async function getEmpresa(id: number | string): Promise<any> {
  const { data } = await api.get(ADMIN_COMPANIES.byId(id))
  return data
}
