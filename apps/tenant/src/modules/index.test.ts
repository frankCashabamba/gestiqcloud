/**
 * Tests for MODULES registry
 */
import { MODULES } from './index'

describe('MODULES registry', () => {
  it('should export MODULES as an array', () => {
    expect(Array.isArray(MODULES)).toBe(true)
  })

  it('should have multiple modules', () => {
    expect(MODULES.length).toBeGreaterThan(5)
  })

  it('should contain pos module', () => {
    const posModule = MODULES.find(m => m.id === 'pos')
    expect(posModule).toBeDefined()
  })

  it('should contain products module', () => {
    const productsModule = MODULES.find(m => m.id === 'products')
    expect(productsModule).toBeDefined()
  })

  it('should contain ventas module', () => {
    const ventasModule = MODULES.find(m => m.id === 'ventas')
    expect(ventasModule).toBeDefined()
  })

  it('should contain inventario module', () => {
    const inventarioModule = MODULES.find(m => m.id === 'inventario')
    expect(inventarioModule).toBeDefined()
  })

  it('should contain crm module', () => {
    const crmModule = MODULES.find(m => m.id === 'crm')
    expect(crmModule).toBeDefined()
  })

  it('all modules should have unique ids', () => {
    const ids = MODULES.map(m => m.id)
    const uniqueIds = new Set(ids)
    expect(uniqueIds.size).toBe(ids.length)
  })

  it('all modules should have id property', () => {
    MODULES.forEach(module => {
      expect(module).toHaveProperty('id')
      expect(typeof module.id).toBe('string')
      expect(module.id.length).toBeGreaterThan(0)
    })
  })

  it('all modules should have name property', () => {
    MODULES.forEach(module => {
      expect(module).toHaveProperty('name')
      expect(typeof module.name).toBe('string')
      expect(module.name.length).toBeGreaterThan(0)
    })
  })

  it('all module ids should be lowercase', () => {
    MODULES.forEach(module => {
      expect(module.id).toBe(module.id.toLowerCase())
    })
  })

  it('all module ids should match pattern', () => {
    const idPattern = /^[a-z][a-z0-9_-]*$/
    MODULES.forEach(module => {
      expect(module.id).toMatch(idPattern)
    })
  })
})
