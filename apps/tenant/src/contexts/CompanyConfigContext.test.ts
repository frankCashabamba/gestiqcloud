import { describe, expect, it } from 'vitest'

import {
  canonicalizeCompanyModuleKey,
  hasCompanyModuleEnabled,
} from '../lib/companyModuleKeys'

describe('CompanyConfigContext module aliases', () => {
  it('keeps canonical english module ids unchanged', () => {
    expect(canonicalizeCompanyModuleKey('manufacturing')).toBe('manufacturing')
    expect(canonicalizeCompanyModuleKey('finance')).toBe('finance')
    expect(canonicalizeCompanyModuleKey('imports')).toBe('imports')
    expect(canonicalizeCompanyModuleKey('customers')).toBe('customers')
  })

  it('does not translate legacy aliases to canonical ids', () => {
    expect(canonicalizeCompanyModuleKey('production')).toBe('production')
    expect(canonicalizeCompanyModuleKey('produccion')).toBe('produccion')
    expect(canonicalizeCompanyModuleKey('finanzas')).toBe('finanzas')
    expect(canonicalizeCompanyModuleKey('finances')).toBe('finances')
    expect(canonicalizeCompanyModuleKey('importador')).toBe('importador')
    expect(canonicalizeCompanyModuleKey('clientes')).toBe('clientes')
    expect(canonicalizeCompanyModuleKey('clients')).toBe('clients')
  })

  it('matches only canonical enabled manufacturing module ids', () => {
    const enabledModules = ['manufacturing']

    expect(hasCompanyModuleEnabled(enabledModules, 'manufacturing')).toBe(true)
    expect(hasCompanyModuleEnabled(enabledModules, 'production')).toBe(false)
    expect(hasCompanyModuleEnabled(enabledModules, 'produccion')).toBe(false)
    expect(hasCompanyModuleEnabled(enabledModules, 'inventory')).toBe(false)
  })

  it('matches only canonical enabled finance module ids', () => {
    const enabledModules = ['finance']

    expect(hasCompanyModuleEnabled(enabledModules, 'finance')).toBe(true)
    expect(hasCompanyModuleEnabled(enabledModules, 'finanzas')).toBe(false)
    expect(hasCompanyModuleEnabled(enabledModules, 'finances')).toBe(false)
  })
})
