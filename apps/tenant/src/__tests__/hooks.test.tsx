/**
 * Tests for custom hooks
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import '@testing-library/jest-dom/vitest'

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

describe('useCountryValidation hook', () => {
  it('should export useCountryValidation function', async () => {
    const { useCountryValidation } = await import('../hooks/useCountryValidation')
    expect(typeof useCountryValidation).toBe('function')
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
