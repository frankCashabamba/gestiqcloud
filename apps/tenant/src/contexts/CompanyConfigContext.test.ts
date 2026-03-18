import { describe, expect, it } from 'vitest'

import {
  canonicalizeCompanyModuleKey,
  hasCompanyModuleEnabled,
} from '../lib/companyModuleKeys'

describe('CompanyConfigContext module aliases', () => {
  it('canonicalizes production aliases to manufacturing', () => {
    expect(canonicalizeCompanyModuleKey('production')).toBe('manufacturing')
    expect(canonicalizeCompanyModuleKey('produccion')).toBe('manufacturing')
    expect(canonicalizeCompanyModuleKey('manufacturing')).toBe('manufacturing')
  })

  it('canonicalizes finance, imports and customers aliases to backend IDs', () => {
    expect(canonicalizeCompanyModuleKey('finanzas')).toBe('finance')
    expect(canonicalizeCompanyModuleKey('finances')).toBe('finance')
    expect(canonicalizeCompanyModuleKey('importador')).toBe('imports')
    expect(canonicalizeCompanyModuleKey('clientes')).toBe('customers')
    expect(canonicalizeCompanyModuleKey('clients')).toBe('customers')
  })

  it('matches enabled manufacturing module through production aliases', () => {
    const enabledModules = ['manufacturing']

    expect(hasCompanyModuleEnabled(enabledModules, 'production')).toBe(true)
    expect(hasCompanyModuleEnabled(enabledModules, 'produccion')).toBe(true)
    expect(hasCompanyModuleEnabled(enabledModules, 'manufacturing')).toBe(true)
    expect(hasCompanyModuleEnabled(enabledModules, 'inventory')).toBe(false)
  })

  it('matches enabled finance module through finance aliases', () => {
    const enabledModules = ['finance']

    expect(hasCompanyModuleEnabled(enabledModules, 'finanzas')).toBe(true)
    expect(hasCompanyModuleEnabled(enabledModules, 'finances')).toBe(true)
    expect(hasCompanyModuleEnabled(enabledModules, 'finance')).toBe(true)
  })
})
