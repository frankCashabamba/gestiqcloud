import { describe, expect, it, vi } from 'vitest'

vi.mock('../../env', () => ({
  env: {
    apiUrl: '/api',
    basePath: '/',
    tenantOrigin: 'https://tenant.test',
    adminOrigin: 'https://admin.test',
    mode: 'test' as const,
    dev: false,
    prod: false,
  },
}))

import { normalizeBaseUrl } from '@shared/api/baseUrl'
import { TENANT_AUTH } from '@shared/endpoints'
import { tenantApiConfig } from './client'

describe('normalizeBaseUrl (shared)', () => {
  it('appends /api for bare origins', () => {
    expect(normalizeBaseUrl('https://tenant.gestiqcloud.com')).toBe('https://tenant.gestiqcloud.com/api')
  })

  it('respects explicit /v1 suffixes', () => {
    expect(normalizeBaseUrl('/v1')).toBe('/v1')
  })
})

describe('tenantApiConfig', () => {
  it('normalizes worker base URL from env', () => {
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
