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

describe('Sales manifest', () => {
  it('should export manifest with required properties', async () => {
    const { manifest } = await import('../modules/sales/manifest')

    expect(manifest).toHaveProperty('id')
    expect(manifest).toHaveProperty('name')
    expect(manifest).toHaveProperty('routes')
  })

  it('should have correct id', async () => {
    const { manifest } = await import('../modules/sales/manifest')
    expect(manifest.id).toBe('sales')
  })

  it('should have routes array', async () => {
    const { manifest } = await import('../modules/sales/manifest')
    expect(Array.isArray(manifest.routes)).toBe(true)
    expect(manifest.routes.length).toBeGreaterThan(0)
  })

  it('should have icon and color', async () => {
    const { manifest } = await import('../modules/sales/manifest')
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

describe('Inventory manifest', () => {
  it('should export inventoryManifest', async () => {
    const { inventoryManifest } = await import('../modules/inventory/manifest')
    expect(inventoryManifest).toBeDefined()
  })

  it('should have required properties', async () => {
    const { inventoryManifest } = await import('../modules/inventory/manifest')
    expect(inventoryManifest).toHaveProperty('id')
    expect(inventoryManifest).toHaveProperty('name')
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

describe('Purchases manifest', () => {
  it('should export manifest', async () => {
    const { manifest } = await import('../modules/purchases/manifest')
    expect(manifest).toBeDefined()
  })
})

describe('Suppliers manifest', () => {
  it('should export manifest', async () => {
    const { manifest } = await import('../modules/suppliers/manifest')
    expect(manifest).toBeDefined()
  })
})

describe('Expenses manifest', () => {
  it('should export manifest', async () => {
    const { manifest } = await import('../modules/expenses/manifest')
    expect(manifest).toBeDefined()
  })
})

describe('Users manifest', () => {
  it('should export manifest', async () => {
    const { manifest } = await import('../modules/users/manifest')
    expect(manifest).toBeDefined()
  })
})

describe('Reports manifest', () => {
  it('should export manifest', async () => {
    const { manifest } = await import('../modules/reports/manifest')
    expect(manifest).toBeDefined()
  })
})
