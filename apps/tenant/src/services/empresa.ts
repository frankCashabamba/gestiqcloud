import api from '../shared/api/client'
import { TENANT_COMPANIES } from '@shared/endpoints'
import { createEmpresaService } from '@shared/domain/empresa'

export type Empresa = { id: number; name: string; slug?: string }

const svc = createEmpresaService(api, {
  base: TENANT_COMPANIES.base,
})

export const getMiEmpresa = svc.getEmpresas
