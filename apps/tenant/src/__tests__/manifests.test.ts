/**
 * Tests for module manifests
 */
import { describe, it, expect } from 'vitest'

describe('POS manifest', () => {
  it('should export manifest with required properties', async () => {
    const { manifest } = await import('../modules/pos/manifest')

    expect(manifest).toHaveProperty('id')
    expect(manifest).toHaveProperty('name')
    expect(manifest).toHaveProperty('version')
    expect(manifest).toHaveProperty('permissions')
    expect(manifest).toHaveProperty('routes')
    expect(manifest).toHaveProperty('menu')
  })

  it('should have correct id', async () => {
    const { manifest } = await import('../modules/pos/manifest')
    expect(manifest.id).toBe('pos')
  })

  it('should have routes array', async () => {
    const { manifest } = await import('../modules/pos/manifest')
    expect(Array.isArray(manifest.routes)).toBe(true)
    expect(manifest.routes.length).toBeGreaterThan(0)
  })

  it('should have permissions array', async () => {
    const { manifest } = await import('../modules/pos/manifest')
    expect(Array.isArray(manifest.permissions)).toBe(true)
    expect(manifest.permissions).toContain('pos.read')
  })

  it('should have menu configuration', async () => {
    const { manifest } = await import('../modules/pos/manifest')
    expect(manifest.menu).toHaveProperty('title')
    expect(manifest.menu).toHaveProperty('icon')
    expect(manifest.menu).toHaveProperty('route')
  })
})

describe('Ventas manifest', () => {
  it('should export manifest with required properties', async () => {
    const { manifest } = await import('../modules/ventas/manifest')

    expect(manifest).toHaveProperty('id')
    expect(manifest).toHaveProperty('name')
    expect(manifest).toHaveProperty('routes')
  })

  it('should have correct id', async () => {
    const { manifest } = await import('../modules/ventas/manifest')
    expect(manifest.id).toBe('ventas')
  })

  it('should have routes array', async () => {
    const { manifest } = await import('../modules/ventas/manifest')
    expect(Array.isArray(manifest.routes)).toBe(true)
    expect(manifest.routes.length).toBeGreaterThan(0)
  })

  it('should have icon and color', async () => {
    const { manifest } = await import('../modules/ventas/manifest')
    expect(manifest.icon).toBeDefined()
    expect(manifest.color).toBeDefined()
  })
})

describe('Productos manifest', () => {
  it('should export productsManifest', async () => {
    const { productsManifest } = await import('../modules/products/manifest')
    expect(productsManifest).toBeDefined()
  })

  it('should have required properties', async () => {
    const { productsManifest } = await import('../modules/products/manifest')
    expect(productsManifest).toHaveProperty('id')
    expect(productsManifest).toHaveProperty('name')
  })
})

describe('Inventario manifest', () => {
  it('should export inventarioManifest', async () => {
    const { inventarioManifest } = await import('../modules/inventario/manifest')
    expect(inventarioManifest).toBeDefined()
  })

  it('should have required properties', async () => {
    const { inventarioManifest } = await import('../modules/inventario/manifest')
    expect(inventarioManifest).toHaveProperty('id')
    expect(inventarioManifest).toHaveProperty('name')
  })
})

describe('CRM manifest', () => {
  it('should export crmManifest', async () => {
    const { crmManifest } = await import('../modules/crm/manifest')
    expect(crmManifest).toBeDefined()
  })

  it('should have required properties', async () => {
    const { crmManifest } = await import('../modules/crm/manifest')
    expect(crmManifest).toHaveProperty('id')
    expect(crmManifest).toHaveProperty('name')
  })
})

describe('Compras manifest', () => {
  it('should export manifest', async () => {
    const { manifest } = await import('../modules/compras/manifest')
    expect(manifest).toBeDefined()
  })
})

describe('Proveedores manifest', () => {
  it('should export manifest', async () => {
    const { manifest } = await import('../modules/proveedores/manifest')
    expect(manifest).toBeDefined()
  })
})

describe('Gastos manifest', () => {
  it('should export manifest', async () => {
    const { manifest } = await import('../modules/gastos/manifest')
    expect(manifest).toBeDefined()
  })
})

describe('Usuarios manifest', () => {
  it('should export manifest', async () => {
    const { manifest } = await import('../modules/usuarios/manifest')
    expect(manifest).toBeDefined()
  })
})

describe('Reportes manifest', () => {
  it('should export manifest', async () => {
    const { manifest } = await import('../modules/reportes/manifest')
    expect(manifest).toBeDefined()
  })
})
