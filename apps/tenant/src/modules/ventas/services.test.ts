import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchVentas, createVenta, deleteVenta } from './services'

// Mock del cliente HTTP
vi.mock('../../lib/http', () => ({
  apiFetch: vi.fn()
}))

import { apiFetch } from '../../lib/http'

describe('Ventas Services', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('fetchVentas', () => {
    it('debería retornar una lista de ventas', async () => {
      const mockVentas = [
        { id: 1, total: 100, fecha: '2025-01-01' },
        { id: 2, total: 200, fecha: '2025-01-02' }
      ]

      vi.mocked(apiFetch).mockResolvedValueOnce(mockVentas)

      const result = await fetchVentas()

      expect(apiFetch).toHaveBeenCalledWith(expect.stringContaining('/sales_orders'))
      expect(result).toEqual(mockVentas)
      expect(Array.isArray(result)).toBe(true)
    })

    it('debería manejar errores de red', async () => {
      vi.mocked(apiFetch).mockRejectedValueOnce(new Error('Network error'))

      await expect(fetchVentas()).rejects.toThrow('Network error')
    })
  })

  describe('createVenta', () => {
    it('debería crear una nueva venta', async () => {
      const nuevaVenta = { cliente_id: 1, total: 150, items: [] }
      const mockResponse = { id: 3, ...nuevaVenta }

      vi.mocked(apiFetch).mockResolvedValueOnce(mockResponse)

      const result = await createVenta(nuevaVenta)

      expect(apiFetch).toHaveBeenCalledWith(
        expect.stringContaining('/sales_orders'),
        expect.objectContaining({
          method: 'POST',
          body: nuevaVenta
        })
      )
      expect(result).toEqual(mockResponse)
    })
  })

  describe('deleteVenta', () => {
    it('debería eliminar una venta por ID', async () => {
      vi.mocked(apiFetch).mockResolvedValueOnce({ success: true })

      await deleteVenta(1)

      expect(apiFetch).toHaveBeenCalledWith(
        expect.stringContaining('/sales_orders/1'),
        expect.objectContaining({ method: 'DELETE' })
      )
    })
  })
})
