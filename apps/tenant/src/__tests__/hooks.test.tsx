/**
 * Tests for custom hooks
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import '@testing-library/jest-dom/vitest'

vi.mock('../env', () => ({
  env: {
    apiUrl: 'http://localhost',
    basePath: '/',
    tenantOrigin: 'http://localhost',
    adminOrigin: 'http://localhost',
    mode: 'test',
    dev: false,
    prod: false,
  },
}))

vi.mock('../lib/http', () => ({
  apiFetch: vi.fn(),
  HttpError: class HttpError extends Error {},
}))

describe('useCurrency hook', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should export useCurrency function', async () => {
    const { useCurrency } = await import('../hooks/useCurrency')
    expect(typeof useCurrency).toBe('function')
  })
})

describe('useMisModulos hook', () => {
  it('should export useMisModulos function', async () => {
    const { useMisModulos } = await import('../hooks/useMisModulos')
    expect(typeof useMisModulos).toBe('function')
  })
})

describe('useSectorConfig hook', () => {
  it('should export useSectorConfig function', async () => {
    const { useSectorConfig } = await import('../hooks/useSectorConfig')
    expect(typeof useSectorConfig).toBe('function')
  })
})

describe('useSectorValidation hook', () => {
  it('should export useSectorValidation function', async () => {
    const { useSectorValidation } = await import('../hooks/useSectorValidation')
    expect(typeof useSectorValidation).toBe('function')
  })
})

describe('useDashboardKPIs hook', () => {
  it('should export useDashboardKPIs function', async () => {
    const { useDashboardKPIs } = await import('../hooks/useDashboardKPIs')
    expect(typeof useDashboardKPIs).toBe('function')
  })
})

describe('useSectorPlaceholders hook', () => {
  it('should export useSectorPlaceholders function', async () => {
    const { useSectorPlaceholders } = await import('../hooks/useSectorPlaceholders')
    expect(typeof useSectorPlaceholders).toBe('function')
  })
})

describe('useSectorValidationRules hook', () => {
  it('should export useSectorValidationRules function', async () => {
    const { useSectorValidationRules } = await import('../hooks/useSectorValidationRules')
    expect(typeof useSectorValidationRules).toBe('function')
  })
})

describe('useCompanySectorFullConfig hook', () => {
  it('should export useCompanySectorFullConfig function', async () => {
    const { useCompanySectorFullConfig } = await import('../hooks/useCompanySectorFullConfig')
    expect(typeof useCompanySectorFullConfig).toBe('function')
  })
})
