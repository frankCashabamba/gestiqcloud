import { describe, expect, it } from 'vitest'

import { TENANT_AUTH } from '@shared/endpoints'
import { tenantApiConfig } from './client'

describe('tenantApiConfig', () => {
  it('uses the worker proxy base', () => {
    expect(tenantApiConfig.baseURL).toBe('/api')
  })

  it('exposes tenant auth endpoints with a consistent prefix', () => {
    const routes = Object.values(TENANT_AUTH)
    expect(routes.every((route) => route.startsWith('/v1/tenant/auth'))).toBe(true)
  })

  it('whitelists login, refresh and logout for unauthenticated flows', () => {
    expect(tenantApiConfig.authExemptSuffixes).toEqual([
      TENANT_AUTH.login,
      TENANT_AUTH.refresh,
      TENANT_AUTH.logout,
    ])
  })
})
