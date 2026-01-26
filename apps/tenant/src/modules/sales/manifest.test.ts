/**
 * Tests for Ventas module manifest
 */
import { manifest } from './manifest'

describe('Ventas manifest', () => {
  it('should have correct id', () => {
    expect(manifest.id).toBe('ventas')
  })

  it('should have name property', () => {
    expect(manifest.name).toBeDefined()
    expect(typeof manifest.name).toBe('string')
    expect(manifest.name.length).toBeGreaterThan(0)
  })

  it('should have icon property', () => {
    expect(manifest.icon).toBeDefined()
  })

  it('should have color property', () => {
    expect(manifest.color).toBeDefined()
    expect(typeof manifest.color).toBe('string')
  })

  it('color should be a valid hex color', () => {
    expect(manifest.color).toMatch(/^#[0-9A-Fa-f]{6}$/)
  })

  it('should have order property', () => {
    expect(manifest.order).toBeDefined()
    expect(typeof manifest.order).toBe('number')
  })

  it('should have routes array', () => {
    expect(Array.isArray(manifest.routes)).toBe(true)
    expect(manifest.routes.length).toBeGreaterThan(0)
  })

  it('routes should have path and label', () => {
    manifest.routes.forEach((route: any) => {
      expect(route).toHaveProperty('path')
      expect(route).toHaveProperty('label')
    })
  })

  it('should have route for list view', () => {
    const listRoute = manifest.routes.find(r => r.path === '')
    expect(listRoute).toBeDefined()
    expect(listRoute?.label).toBe('Todas')
  })

  it('should have route for new sale', () => {
    const newRoute = manifest.routes.find(r => r.path === 'nueva')
    expect(newRoute).toBeDefined()
    expect(newRoute?.label).toBe('Nueva')
  })
})
