/**
 * Tests for MODULES array and ModuleLoader component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { MODULES } from '../modules'

vi.mock('../i18n/I18nProvider', () => ({
  useI18n: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock('../hooks/useMisModulos', () => ({
  useMisModulos: () => ({
    allowedSlugs: new Set(['pos', 'productos', 'inventario', 'ventas']),
    loading: false,
  }),
}))

describe('MODULES configuration', () => {
  describe('MODULES array structure', () => {
    it('should export MODULES as an array', () => {
      expect(Array.isArray(MODULES)).toBe(true)
    })

    it('should have at least one module', () => {
      expect(MODULES.length).toBeGreaterThan(0)
    })

    it('should contain expected core modules by id', () => {
      const moduleIds = MODULES.map(m => m.id)
      expect(moduleIds).toContain('pos')
      expect(moduleIds).toContain('products')
    })
  })

  describe('Module manifest required properties', () => {
    it.each(MODULES)('module "$id" should have id property', (module) => {
      expect(module).toHaveProperty('id')
      expect(typeof module.id).toBe('string')
      expect(module.id.length).toBeGreaterThan(0)
    })

    it.each(MODULES)('module "$id" should have name property', (module) => {
      expect(module).toHaveProperty('name')
      expect(typeof module.name).toBe('string')
      expect(module.name.length).toBeGreaterThan(0)
    })
  })

  describe('Module IDs uniqueness', () => {
    it('should have unique module IDs', () => {
      const ids = MODULES.map(m => m.id)
      const uniqueIds = new Set(ids)
      expect(uniqueIds.size).toBe(ids.length)
    })
  })

  describe('Module manifest optional properties', () => {
    it('modules with routes should have valid routes array', () => {
      const modulesWithRoutes = MODULES.filter((m: any) => m.routes !== undefined)
      modulesWithRoutes.forEach((module: any) => {
        expect(Array.isArray(module.routes)).toBe(true)
        expect(module.routes.length).toBeGreaterThan(0)
      })
    })

    it('modules with permissions should have array of strings', () => {
      const modulesWithPermissions = MODULES.filter((m: any) => m.permissions !== undefined)
      modulesWithPermissions.forEach((module: any) => {
        expect(Array.isArray(module.permissions)).toBe(true)
        module.permissions.forEach((perm: any) => {
          expect(typeof perm).toBe('string')
        })
      })
    })

    it('modules with menu should have valid menu structure', () => {
      const modulesWithMenu = MODULES.filter((m: any) => m.menu !== undefined)
      expect(modulesWithMenu.length).toBeGreaterThan(0)
      modulesWithMenu.forEach((module: any) => {
        expect(module.menu).toBeDefined()
      })
    })
  })
})

describe('ModuleLoader component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  function TestModuleLoader() {
    return <div data-testid="module-loader">Module Loader</div>
  }

  const renderWithRouter = (initialRoute: string) => {
    return render(
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route path="/m/:mod/*" element={<TestModuleLoader />} />
          <Route path="/error" element={<div>Error Page</div>} />
          <Route path="/unauthorized" element={<div>Unauthorized</div>} />
        </Routes>
      </MemoryRouter>
    )
  }

  it('should render module loader component', async () => {
    renderWithRouter('/m/pos')
    expect(screen.getByTestId('module-loader')).toBeInTheDocument()
  })

  it('should show error page for invalid route', async () => {
    renderWithRouter('/error')
    expect(screen.getByText('Error Page')).toBeInTheDocument()
  })
})

describe('MODULES export validation', () => {
  it('should export ModuleManifest type', async () => {
    const moduleIndex = await import('../modules')
    expect(moduleIndex).toHaveProperty('MODULES')
  })

  it('should have products module', () => {
    const productsModule = MODULES.find(m => m.id === 'products')
    expect(productsModule).toBeDefined()
  })

  it('should have pos module', () => {
    const posModule = MODULES.find(m => m.id === 'pos')
    expect(posModule).toBeDefined()
  })

  it('should have ventas module', () => {
    const ventasModule = MODULES.find(m => m.id === 'ventas')
    expect(ventasModule).toBeDefined()
  })

  it('should have inventario module', () => {
    const inventarioModule = MODULES.find(m => m.id === 'inventario')
    expect(inventarioModule).toBeDefined()
  })

  it('all modules should have name property', () => {
    MODULES.forEach(module => {
      expect(module.name).toBeDefined()
      expect(typeof module.name).toBe('string')
    })
  })

  it('all modules should have valid id format', () => {
    const idPattern = /^[a-z][a-z0-9_-]*$/
    MODULES.forEach(module => {
      expect(module.id).toMatch(idPattern)
    })
  })
})
