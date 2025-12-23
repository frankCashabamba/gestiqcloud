/**
 * Tests para useUnits hook
 *
 * Verificar que:
 * - Carga unidades desde API correctamente
 * - Cachea resultados (no re-fetches)
 * - Maneja errores gracefully
 * - Usa fallback a default units
 */

import { renderHook, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { useUnitsBySector, clearUnitsCache } from './useUnits'
import * as unitService from '../services/unitService'

// Mock de unitService
vi.mock('../services/unitService', () => ({
  getSectorUnits: vi.fn(),
  getDefaultUnits: vi.fn(() => [
    { code: 'unit', label: 'Unidad' },
    { code: 'kg', label: 'Kilogramo' },
  ]),
}))

describe('useUnits - useUnitsBySector', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    clearUnitsCache()
  })

  it('should load units from API for valid sector', async () => {
    const mockUnits = [
      { code: 'unit', label: 'Unidad' },
      { code: 'kg', label: 'Kilogramo' },
      { code: 'g', label: 'Gramo' },
      { code: 'dozen', label: 'Docena' },
    ]

    vi.mocked(unitService.getSectorUnits).mockResolvedValue(mockUnits)

    const { result } = renderHook(() => useUnitsBySector('panaderia'))

    // Initially loading
    expect(result.current.loading).toBe(true)
    expect(result.current.units.length).toBeGreaterThan(0) // defaults

    // After load
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.units).toEqual(mockUnits)
    expect(result.current.error).toBeNull()
  })

  it('should use default units when no sector provided', async () => {
    const mockDefaults = [
      { code: 'unit', label: 'Unidad' },
      { code: 'kg', label: 'Kilogramo' },
    ]

    const { result } = renderHook(() => useUnitsBySector(null))

    expect(result.current.units).toEqual(mockDefaults)
    expect(result.current.loading).toBe(false)
    expect(vi.mocked(unitService.getSectorUnits)).not.toHaveBeenCalled()
  })

  it('should handle API errors gracefully', async () => {
    const errorMessage = 'API Error'
    vi.mocked(unitService.getSectorUnits).mockRejectedValue(
      new Error(errorMessage)
    )

    const { result } = renderHook(() => useUnitsBySector('invalid-sector'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBeDefined()
    expect(result.current.units).toBeDefined() // Falls back to defaults
  })

  it('should cache units and not re-fetch for same sector', async () => {
    const mockUnits = [
      { code: 'unit', label: 'Unidad' },
      { code: 'taller', label: 'Taller' },
    ]

    vi.mocked(unitService.getSectorUnits).mockResolvedValue(mockUnits)

    // First render
    const { result: result1 } = renderHook(() => useUnitsBySector('taller'))

    await waitFor(() => {
      expect(result1.current.loading).toBe(false)
    })

    expect(vi.mocked(unitService.getSectorUnits)).toHaveBeenCalledTimes(1)
    expect(result1.current.units).toEqual(mockUnits)

    // Second render - should use cache
    const { result: result2 } = renderHook(() => useUnitsBySector('taller'))

    expect(result2.current.loading).toBe(false)
    expect(result2.current.units).toEqual(mockUnits)

    // API should not have been called again
    expect(vi.mocked(unitService.getSectorUnits)).toHaveBeenCalledTimes(1)
  })

  it('should update when sector code changes', async () => {
    const panaderiaUnits = [
      { code: 'kg', label: 'Kilogramo' },
      { code: 'dozen', label: 'Docena' },
    ]
    const tallerUnits = [
      { code: 'unit', label: 'Unidad' },
      { code: 'pair', label: 'Par' },
    ]

    vi.mocked(unitService.getSectorUnits)
      .mockResolvedValueOnce(panaderiaUnits)
      .mockResolvedValueOnce(tallerUnits)

    const { result, rerender } = renderHook(
      ({ sector }) => useUnitsBySector(sector),
      { initialProps: { sector: 'panaderia' } }
    )

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.units).toEqual(panaderiaUnits)

    // Change sector
    rerender({ sector: 'taller' })

    await waitFor(() => {
      expect(result.current.units).toEqual(tallerUnits)
    })
  })
})
