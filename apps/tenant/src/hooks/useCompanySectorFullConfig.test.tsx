import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useCompanySectorFullConfig } from './useCompanySectorFullConfig'

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

vi.mock('../services/unitService', () => ({
  getDefaultUnits: () => [],
}))

describe('useCompanySectorFullConfig', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    cache.clear()
  })

  it('falls back to cached config when the sector endpoint is offline', async () => {
    const cachedSector = {
      code: 'panaderia',
      name: 'Panaderia',
      branding: {
        icon: 'B',
        displayName: 'Panaderia',
        color_primario: '#111827',
        units: [],
        format_rules: {},
        print_config: { width: 80, fontSize: 12, showLogo: true, showDetails: true },
        required_fields: {},
      },
      fields: {},
      features: {
        expiry_tracking: true,
        lot_tracking: true,
        serial_tracking: false,
        batch_tracking: true,
        weight_tracking: false,
      },
      defaults: {
        categories: [],
        tax_rate: 12,
        currency: 'EUR',
        locale: 'es',
        timezone: 'Europe/Madrid',
        price_includes_tax: true,
      },
      endpoints: { imports: '/imports', products: '/products', customers: '/customers' },
      templates: { allowed: ['default'] },
    }

    cache.set('sector-full-config:panaderia:tenant-scope', cachedSector)
    apiFetchMock.mockRejectedValueOnce(new Error('Failed to fetch'))

    const { result } = renderHook(() => useCompanySectorFullConfig('panaderia'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.config).toEqual(cachedSector)
    expect(result.current.error).toBeNull()
  })
})
