import api from '../shared/api/client'
import { TENANT_EMPRESAS } from '@shared/endpoints'
import { createEmpresaService } from '@shared/domain/empresa'

export type Empresa = { id: number; name: string; slug?: string }

const svc = createEmpresaService(api, {
  base: TENANT_EMPRESAS.base,
})

export const getMiEmpresa = svc.getEmpresas
