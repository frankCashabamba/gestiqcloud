/**
 * Test para useBusinessCategories
 *
 * Verificar que el hook:
 * - Carga categorías desde API
 * - Cachea resultados
 * - Maneja errores correctamente
 */

import { renderHook, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { useBusinessCategories } from './useBusinessCategories'
import * as api from '../services/businessCategoriesApi'

// Mock de la API
vi.mock('../services/businessCategoriesApi', () => ({
  getBusinessCategories: vi.fn(),
  getBusinessCategoryByCode: vi.fn(),
}))

describe('useBusinessCategories', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should load categories from API', async () => {
    const mockCategories = [
      { id: '1', code: 'retail', name: 'Retail', description: 'Tienda' },
      { id: '2', code: 'services', name: 'Servicios', description: 'Servicios' },
    ]

    vi.mocked(api.getBusinessCategories).mockResolvedValue(mockCategories)

    const { result } = renderHook(() => useBusinessCategories())

    // Initially loading
    expect(result.current.loading).toBe(true)
    expect(result.current.categories).toEqual([])
    expect(result.current.error).toBeNull()

    // After load
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.categories).toEqual(mockCategories)
    expect(result.current.error).toBeNull()
  })

  it('should handle errors gracefully', async () => {
    const errorMessage = 'Failed to fetch categories'
    vi.mocked(api.getBusinessCategories).mockRejectedValue(
      new Error(errorMessage)
    )

    const { result } = renderHook(() => useBusinessCategories())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.categories).toEqual([])
    expect(result.current.error).toBeDefined()
  })

  it('should not call API if data is cached', async () => {
    const mockCategories = [
      { id: '1', code: 'retail', name: 'Retail', description: 'Tienda' },
    ]

    vi.mocked(api.getBusinessCategories).mockResolvedValue(mockCategories)

    const { result: result1 } = renderHook(() => useBusinessCategories())

    await waitFor(() => {
      expect(result1.current.loading).toBe(false)
    })

    expect(vi.mocked(api.getBusinessCategories)).toHaveBeenCalledTimes(1)

    // Second call should use cache
    const { result: result2 } = renderHook(() => useBusinessCategories())

    await waitFor(() => {
      expect(result2.current.loading).toBe(false)
    })

    expect(vi.mocked(api.getBusinessCategories)).toHaveBeenCalledTimes(1) // Still 1, not 2
  })
})
