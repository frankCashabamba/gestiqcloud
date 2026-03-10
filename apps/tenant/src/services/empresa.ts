import api from '../shared/api/client'
import { TENANT_COMPANIES } from '@shared/endpoints'
import { createEmpresaService } from '@shared/domain/empresa'
import { isNetworkIssue } from '../lib/offlineHttp'
import { getOfflineCacheScope, readCachedResource, writeCachedResource } from '../lib/offlineResourceCache'

export type Empresa = { id: number; name: string; slug?: string }

const svc = createEmpresaService(api, {
  base: TENANT_COMPANIES.base,
})

function companyCacheKey() {
  return `company:mine:${getOfflineCacheScope()}`
}

export async function getMiEmpresa() {
  const key = companyCacheKey()

  try {
    const data = await svc.getEmpresas()
    writeCachedResource(key, data)
    return data
  } catch (error) {
    const cached = readCachedResource<Empresa[]>(key)
    if (cached?.length && isNetworkIssue(error)) {
      return cached
    }
    throw error
  }
}
