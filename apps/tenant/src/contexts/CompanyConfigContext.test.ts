import { describe, expect, it } from 'vitest'

import {
  canonicalizeCompanyModuleKey,
  hasCompanyModuleEnabled,
} from '../lib/companyModuleKeys'

describe('CompanyConfigContext module aliases', () => {
  it('canonicalizes production aliases to manufacturing', () => {
    expect(canonicalizeCompanyModuleKey('production')).toBe('manufacturing')
    expect(canonicalizeCompanyModuleKey('producción')).toBe('manufacturing')
    expect(canonicalizeCompanyModuleKey('manufacturing')).toBe('manufacturing')
  })

  it('matches enabled manufacturing module through production aliases', () => {
    const enabledModules = ['manufacturing']

    expect(hasCompanyModuleEnabled(enabledModules, 'production')).toBe(true)
    expect(hasCompanyModuleEnabled(enabledModules, 'produccion')).toBe(true)
    expect(hasCompanyModuleEnabled(enabledModules, 'manufacturing')).toBe(true)
    expect(hasCompanyModuleEnabled(enabledModules, 'inventory')).toBe(false)
  })
})
