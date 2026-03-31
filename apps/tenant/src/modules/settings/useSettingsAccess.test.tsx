import { describe, expect, it } from 'vitest'

import { isBakeryOperativeSector } from './sectorRules'

describe('isBakeryOperativeSector', () => {
  it('accepts bakery aliases', () => {
    expect(isBakeryOperativeSector('panaderia')).toBe(true)
    expect(isBakeryOperativeSector('Panaderia_Pro')).toBe(true)
    expect(isBakeryOperativeSector('bakery')).toBe(true)
    expect(isBakeryOperativeSector(' bakery_pro ')).toBe(true)
  })

  it('rejects non bakery sectors', () => {
    expect(isBakeryOperativeSector('retail')).toBe(false)
    expect(isBakeryOperativeSector('taller')).toBe(false)
    expect(isBakeryOperativeSector('')).toBe(false)
    expect(isBakeryOperativeSector(null)).toBe(false)
  })
})
