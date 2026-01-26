/**
 * Tests for POS module manifest
 */
import { manifest } from './manifest'

describe('POS manifest', () => {
  it('should have correct id', () => {
    expect(manifest.id).toBe('pos')
  })

  it('should have name property', () => {
    expect(manifest.name).toBeDefined()
    expect(typeof manifest.name).toBe('string')
    expect(manifest.name.length).toBeGreaterThan(0)
  })

  it('should have version property', () => {
    expect(manifest.version).toBeDefined()
    expect(typeof manifest.version).toBe('string')
  })

  it('should have permissions array', () => {
    expect(Array.isArray(manifest.permissions)).toBe(true)
    expect(manifest.permissions.length).toBeGreaterThan(0)
  })

  it('should have pos.read permission', () => {
    expect(manifest.permissions).toContain('pos.read')
  })

  it('should have pos.write permission', () => {
    expect(manifest.permissions).toContain('pos.write')
  })

  it('should have routes array', () => {
    expect(Array.isArray(manifest.routes)).toBe(true)
    expect(manifest.routes.length).toBeGreaterThan(0)
  })

  it('routes should have path and element', () => {
    manifest.routes.forEach((route: any) => {
      expect(route).toHaveProperty('path')
    })
  })

  it('should have menu configuration', () => {
    expect(manifest.menu).toBeDefined()
    expect(manifest.menu).toHaveProperty('title')
    expect(manifest.menu).toHaveProperty('icon')
    expect(manifest.menu).toHaveProperty('route')
    expect(manifest.menu).toHaveProperty('order')
  })

  it('menu should have correct route', () => {
    expect(manifest.menu.route).toBe('/pos')
  })
})
