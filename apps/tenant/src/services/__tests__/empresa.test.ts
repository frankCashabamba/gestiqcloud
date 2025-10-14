import { afterEach, describe, expect, it } from 'vitest'
import { TENANT_EMPRESAS } from '@shared/endpoints'

import { loadTenantServiceModule, restoreTenantModules } from './helpers'

describe('tenant empresa service routes', () => {
  afterEach(() => {
    restoreTenantModules()
  })

  it('delegates empresa reads to the shared domain base route', async () => {
    const {
      module: { getMiEmpresa },
      api,
    } = await loadTenantServiceModule<typeof import('../empresa')>('../empresa')

    await getMiEmpresa()

    expect(api.get).toHaveBeenCalledWith(TENANT_EMPRESAS.base)
  })
})
