/**
 * Tests for services
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import '@testing-library/jest-dom/vitest'

describe('modulos service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.resetModules()
  })

  it('should export listMisModulos function', async () => {
    const modulos = await import('../services/modules')
    expect(typeof modulos.listMisModulos).toBe('function')
  })

  it('should export listModulosSeleccionablesPorEmpresa function', async () => {
    const modulos = await import('../services/modules')
    expect(typeof modulos.listModulosSeleccionablesPorEmpresa).toBe('function')
  })
})

describe('unitService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should export getSectorUnits function', async () => {
    const unitService = await import('../services/unitService')
    expect(typeof unitService.getSectorUnits).toBe('function')
  })

  it('should export getDefaultUnits function', async () => {
    const unitService = await import('../services/unitService')
    expect(typeof unitService.getDefaultUnits).toBe('function')
  })

  it('should export getUnitByCode function', async () => {
    const unitService = await import('../services/unitService')
    expect(typeof unitService.getUnitByCode).toBe('function')
  })

  it('should export formatWithUnit function', async () => {
    const unitService = await import('../services/unitService')
    expect(typeof unitService.formatWithUnit).toBe('function')
  })

  it('getDefaultUnits should return array of units', async () => {
    const { getDefaultUnits } = await import('../services/unitService')
    const units = getDefaultUnits()

    expect(Array.isArray(units)).toBe(true)
    expect(units.length).toBeGreaterThan(0)
    expect(units[0]).toHaveProperty('code')
    expect(units[0]).toHaveProperty('label')
  })

  it('getDefaultUnits should include common units', async () => {
    const { getDefaultUnits } = await import('../services/unitService')
    const units = getDefaultUnits()
    const codes = units.map(u => u.code)

    expect(codes).toContain('unit')
    expect(codes).toContain('kg')
    expect(codes).toContain('l')
  })

  it('formatWithUnit should format value with unit label', async () => {
    const { formatWithUnit, getDefaultUnits } = await import('../services/unitService')
    const units = getDefaultUnits()

    const formatted = formatWithUnit(5, 'kg', units)
    expect(formatted).toContain('5')
    expect(formatted).toContain('Kilogramo')
  })

  it('formatWithUnit should use code as fallback when unit not found', async () => {
    const { formatWithUnit } = await import('../services/unitService')

    const formatted = formatWithUnit(10, 'unknown_unit', [])
    expect(formatted).toBe('10 unknown_unit')
  })
})

describe('theme service', () => {
  it('should export theme service', async () => {
    const theme = await import('../services/theme')
    expect(theme).toBeDefined()
  })
})

describe('empresa service', () => {
  it('should export empresa service', async () => {
    const empresa = await import('../services/empresa')
    expect(empresa).toBeDefined()
  })
})

describe('companySettings service', () => {
  it('should export companySettings service', async () => {
    const companySettings = await import('../services/companySettings')
    expect(companySettings).toBeDefined()
  })
})

describe('businessCategoriesApi service', () => {
  it('should export businessCategoriesApi service', async () => {
    const businessCategoriesApi = await import('../services/businessCategoriesApi')
    expect(businessCategoriesApi).toBeDefined()
  })
})
