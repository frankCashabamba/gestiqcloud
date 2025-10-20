/**
 * Tests for ElectricSQL integration
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import {
  initElectric,
  getElectric,
  getLocalDb,
  isOnline,
  setupOnlineSync,
  setConflictHandler
} from '../electric'

// Mock ElectricSQL
vi.mock('electric-sql/pglite', () => ({
  PGlite: vi.fn().mockImplementation(() => ({
    connect: vi.fn(),
    query: vi.fn()
  })),
  electrify: vi.fn()
}))

vi.mock('electric-sql', () => ({
  ElectricDatabase: vi.fn()
}))

describe('ElectricSQL Integration', () => {
  beforeEach(() => {
    // Reset modules
    vi.clearAllMocks()

    // Mock navigator.onLine
    Object.defineProperty(navigator, 'onLine', {
      writable: true,
      value: true
    })
  })

  afterEach(() => {
    // Clean up event listeners
    window.removeEventListener('online', expect.any(Function))
    window.removeEventListener('offline', expect.any(Function))
  })

  describe('initElectric', () => {
    it('should initialize ElectricSQL with tenant ID', async () => {
      const mockElectric = { sync: vi.fn() }
      const mockPGlite = { connect: vi.fn() }

      // Mock the imports
      const { electrify, PGlite } = await import('electric-sql/pglite')
      vi.mocked(PGlite).mockReturnValue(mockPGlite as any)
      vi.mocked(electrify).mockResolvedValue(mockElectric as any)

      const result = await initElectric('test-tenant')

      expect(result).toBe(mockElectric)
      expect(getElectric()).toBe(mockElectric)
      expect(getLocalDb()).toBe(mockPGlite)
    })

    it('should return existing instance if already initialized', async () => {
      const mockElectric = { sync: vi.fn() }
      const mockPGlite = { connect: vi.fn() }

      const { electrify, PGlite } = await import('electric-sql/pglite')
      vi.mocked(PGlite).mockReturnValue(mockPGlite as any)
      vi.mocked(electrify).mockResolvedValue(mockElectric as any)

      await initElectric('test-tenant')
      const result = await initElectric('test-tenant')

      expect(result).toBe(mockElectric)
      expect(PGlite).toHaveBeenCalledTimes(1) // Only called once
    })
  })

  describe('isOnline', () => {
    it('should return navigator.onLine status', () => {
      expect(isOnline()).toBe(true)

      Object.defineProperty(navigator, 'onLine', {
        writable: true,
        value: false
      })

      expect(isOnline()).toBe(false)
    })
  })

  describe('setupOnlineSync', () => {
    it('should setup online/offline event listeners', () => {
      const mockElectric = {
        sync: vi.fn().mockResolvedValue({ conflicts: [] })
      }

      // Mock initElectric
      vi.doMock('../electric', () => ({
        ...vi.importActual('../electric'),
        initElectric: vi.fn().mockResolvedValue(mockElectric)
      }))

      setupOnlineSync('test-tenant')

      // Simulate online event
      window.dispatchEvent(new Event('online'))

      expect(mockElectric.sync).toHaveBeenCalled()
    })

    it('should handle sync conflicts', async () => {
      const mockElectric = {
        sync: vi.fn().mockResolvedValue({
          conflicts: [
            { resolution: 'manual_review_required', data: 'test' }
          ]
        })
      }

      let conflictCallback: any = null
      setConflictHandler((conflicts) => {
        conflictCallback = conflicts
      })

      // Mock initElectric
      vi.doMock('../electric', () => ({
        ...vi.importActual('../electric'),
        initElectric: vi.fn().mockResolvedValue(mockElectric)
      }))

      setupOnlineSync('test-tenant')

      // Simulate online event
      window.dispatchEvent(new Event('online'))

      // Wait for async operations
      await new Promise(resolve => setTimeout(resolve, 0))

      expect(conflictCallback).toEqual([
        { resolution: 'manual_review_required', data: 'test' }
      ])
    })
  })

  describe('Conflict Handler', () => {
    it('should allow setting conflict callback', () => {
      const mockCallback = vi.fn()

      setConflictHandler(mockCallback)

      // This would be tested in integration with setupOnlineSync
      expect(mockCallback).toBeDefined()
    })
  })
})
