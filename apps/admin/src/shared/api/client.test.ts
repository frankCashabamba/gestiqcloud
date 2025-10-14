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

import { ADMIN_AUTH } from '@shared/endpoints'
import { adminApiConfig, normalizeBaseUrl } from './client'

describe('normalizeBaseUrl', () => {
  const cases: Array<{ input: string; expected: string }> = [
    { input: '', expected: '/api' },
    { input: '   ', expected: '/api' },
    { input: '/api', expected: '/api' },
    { input: '/api/', expected: '/api' },
    { input: '/v1', expected: '/v1' },
    { input: '/v1/', expected: '/v1' },
    { input: 'https://admin.gestiqcloud.com', expected: 'https://admin.gestiqcloud.com/api' },
    { input: 'https://admin.gestiqcloud.com/', expected: 'https://admin.gestiqcloud.com/api' },
    { input: 'https://admin.gestiqcloud.com/api', expected: 'https://admin.gestiqcloud.com/api' },
    { input: 'https://admin.gestiqcloud.com/v1', expected: 'https://admin.gestiqcloud.com/v1' },
    { input: 'https://admin.gestiqcloud.com/v1/', expected: 'https://admin.gestiqcloud.com/v1' },
  ]

  cases.forEach(({ input, expected }) => {
    it(`normalizes "${input}" -> "${expected}"`, () => {
      expect(normalizeBaseUrl(input)).toBe(expected)
    })
  })
})

describe('adminApiConfig', () => {
  it('normalizes baseURL from env at module load', () => {
    expect(adminApiConfig.baseURL).toBe('/api')
  })

  it('whitelists every admin auth route for unauthenticated requests', () => {
    expect(adminApiConfig.authExemptSuffixes).toEqual([
      ADMIN_AUTH.login,
      ADMIN_AUTH.refresh,
      ADMIN_AUTH.logout,
      '/v1/auth/login',
      '/v1/auth/refresh',
      '/v1/auth/logout',
    ])
  })

  it('keeps all admin auth endpoints versioned under /v1/admin/auth', () => {
    const routes = Object.values(ADMIN_AUTH)
    expect(routes.every((route) => route.startsWith('/v1/admin/auth'))).toBe(true)
  })
})
