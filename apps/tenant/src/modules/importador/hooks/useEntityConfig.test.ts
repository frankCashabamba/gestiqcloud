import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, beforeEach, vi } from 'vitest'
import { useEntityConfig } from './useEntityConfig'
import { clearEntityConfigCache } from '../config/entityTypes'

const apiFetchMock = vi.fn()

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ profile: { empresa_slug: 'acme' } }),
}))

vi.mock('../../../lib/http', () => ({
  apiFetch: (...args: any[]) => apiFetchMock(...args),
}))

describe('useEntityConfig', () => {
  beforeEach(() => {
    clearEntityConfigCache()
    apiFetchMock.mockResolvedValue({
      module: 'products',
      items: [
        {
          field: 'precio_venta',
          aliases: ['pvp', 'price'],
          field_type: 'integer',
          validation_pattern: '^\\d+$',
          transform_expression: 'return parseFloat(String(v).replace(/[^\\d.-]/g, ""))',
        },
      ],
    })
  })

  it('carga config dinámica y mapea field_type/regex/transform', async () => {
    const { result } = renderHook(() => useEntityConfig({ module: 'products' }))

    await waitFor(() => expect(result.current.loading).toBe(false))

    const field = result.current.config?.fields.find((f) => f.field === 'precio_venta')
    expect(field?.type).toBe('number') // field_type=integer -> number
    expect(field?.aliases).toContain('pvp')
    expect(field?.validation?.('123')).toBe(true)
    expect(field?.validation?.('abc')).toBe(false)
    expect(field?.transform?.('12,3')).toBe(123)
  })
})
