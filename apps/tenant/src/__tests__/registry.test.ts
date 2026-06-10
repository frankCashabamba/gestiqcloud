import { describe, it, expect } from 'vitest'
import { moduleRegistry, manifestPaths, moduleCount } from '../modules/registry'

describe('module manifest registry', () => {
  it('discovers every modules/<name>/manifest.ts via import.meta.glob', () => {
    // 28 modules ship a manifest.ts today. If you add or remove a module,
    // update this assertion deliberately.
    expect(manifestPaths.length).toBe(28)
  })

  it('registers a manifest object (with `id`) for every discovered file', () => {
    // No silent drops — every glob-discovered manifest.ts must yield a
    // registered entry.
    expect(moduleCount).toBe(manifestPaths.length)
  })

  it('exposes well-known module ids', () => {
    for (const id of ['pos', 'sales', 'products', 'inventory', 'crm', 'accounting']) {
      expect(moduleRegistry.has(id), `missing module: ${id}`).toBe(true)
    }
  })
})
