import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import { CompanyConfigProvider, useCompanyFeatures } from './CompanyConfigContext'

const apiFetchMock = vi.fn()
const cache = new Map<string, unknown>()

vi.mock('../lib/http', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}))

vi.mock('../lib/offlineResourceCache', () => ({
  getOfflineCacheScope: () => 'tenant-scope',
  readCachedResource: (key: string) => cache.get(key) ?? null,
  writeCachedResource: (key: string, value: unknown) => {
    cache.set(key, value)
  },
}))

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({
    token: 'tenant-token',
    loading: false,
  }),
}))

vi.mock('../hooks/useCompanySectorFullConfig', () => ({
  useCompanySectorFullConfig: () => ({
    config: null,
    loading: false,
  }),
}))

vi.mock('../i18n', () => ({
  default: {
    resolvedLanguage: 'es',
    changeLanguage: vi.fn(),
  },
  normalizeLang: (value?: string | null) => value || 'es',
}))

function Probe() {
  const features = useCompanyFeatures()
  return (
    <div>
      <span data-testid="production">{String(features.production_enabled)}</span>
      <span data-testid="billing">{String((features as any).billing_enabled)}</span>
    </div>
  )
}

describe('CompanyConfigProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    cache.clear()
    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/v1/company/settings/config') {
        return Promise.resolve({
          tenant: { id: 'tenant-1', name: 'Demo', color_primario: '#000', plantilla_inicio: 'default', currency: 'EUR', country: 'ES', config_json: {} },
          settings: { settings: {}, pos_config: {}, locale: 'es', timezone: 'Europe/Madrid', currency: 'EUR' },
          categories: [],
          enabled_modules: [],
          features: { production_enabled: true },
          sector: { plantilla: 'default', features: {} },
        })
      }
      if (url === '/api/v1/feature-flags') {
        return Promise.resolve({
          flags: {
            production_enabled: false,
            billing_enabled: true,
          },
        })
      }
      return Promise.reject(new Error(`Unexpected URL ${url}`))
    })
  })

  it('merges resolved backend feature flags over config features', async () => {
    render(
      <CompanyConfigProvider>
        <Probe />
      </CompanyConfigProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('production').textContent).toBe('false')
    })
    expect(screen.getByTestId('billing').textContent).toBe('true')
  })

  it('uses cached company config when the backend is offline', async () => {
    cache.set('company-config:tenant-scope', {
      company: { id: 'tenant-1', name: 'Demo', color_primario: '#000', plantilla_inicio: 'default', currency: 'EUR', country: 'ES', config_json: {} },
      settings: { settings: {}, pos_config: {}, locale: 'es', timezone: 'Europe/Madrid', currency: 'EUR' },
      categories: [],
      enabled_modules: [],
      features: { production_enabled: true, billing_enabled: false },
      sector: { plantilla: 'default', features: {} },
    })

    apiFetchMock.mockRejectedValueOnce(new Error('Failed to fetch'))
    apiFetchMock.mockRejectedValueOnce(new Error('Failed to fetch'))

    render(
      <CompanyConfigProvider>
        <Probe />
      </CompanyConfigProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('production').textContent).toBe('true')
    })
    expect(screen.getByTestId('billing').textContent).toBe('false')
  })
})
