import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../../shared/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

vi.mock('../../lib/offlineStore', () => ({
  storeEntity: vi.fn(),
  queueDeletion: vi.fn(),
}))

vi.mock('../../lib/offlineHttp', () => ({
  createOfflineTempId: vi.fn(() => 'temp-1'),
  isNetworkIssue: vi.fn(() => false),
  isOfflineQueuedResponse: vi.fn(() => false),
  stripOfflineMeta: vi.fn((p: any) => p),
}))

import tenantApi from '../../shared/api/client'

describe('Ventas Services', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listVentas', () => {
    it('debería retornar una lista de ventas', async () => {
      const mockVentas = [
        { id: 1, total: 100, order_date: '2025-01-01' },
        { id: 2, total: 200, order_date: '2025-01-02' },
      ]

      vi.mocked(tenantApi.get).mockResolvedValueOnce({ data: mockVentas } as any)

      const { listVentas } = await import('./services')
      const result = await listVentas()

      expect(tenantApi.get).toHaveBeenCalled()
      expect(Array.isArray(result)).toBe(true)
      expect(result).toHaveLength(2)
    })

    it('debería manejar errores de red', async () => {
      vi.mocked(tenantApi.get).mockRejectedValueOnce(new Error('Network error'))

      const { listVentas } = await import('./services')
      await expect(listVentas()).rejects.toThrow('Network error')
    })
  })

  describe('createVenta', () => {
    it('debería crear una nueva venta', async () => {
      const nuevaVenta = { cliente_id: 1, total: 150, fecha: '2025-01-01', lineas: [] }
      const mockResponse = { id: 3, ...nuevaVenta }

      vi.mocked(tenantApi.post).mockResolvedValueOnce({ data: mockResponse } as any)

      const { createVenta } = await import('./services')
      const result = await createVenta(nuevaVenta as any)

      expect(tenantApi.post).toHaveBeenCalled()
      expect(result).toBeDefined()
    })
  })

  describe('removeVenta', () => {
    it('debería eliminar una venta por ID', async () => {
      vi.mocked(tenantApi.delete).mockResolvedValueOnce({ data: { success: true } } as any)

      const { removeVenta } = await import('./services')
      await removeVenta(1)

      expect(tenantApi.delete).toHaveBeenCalled()
    })
  })
})
