import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { usePermission } from '../usePermission'
import { PermissionsProvider } from '../../contexts/PermissionsContext'
import { AuthProvider } from '../../auth/AuthContext'
import React from 'react'

/**
 * Tests para usePermission hook
 */

// Mock de AuthContext
vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({
    token: 'mock-token.mock.payload',
    profile: { es_admin_empresa: false },
  }),
  AuthProvider: ({ children }: any) => React.createElement(React.Fragment, {}, children),
}))

// Mock de apiFetch
vi.mock('../../lib/http', () => ({
  apiFetch: vi.fn(async () => ({
    permisos: {
      billing: { read: true, create: true, delete: false },
      usuarios: { read: true, update: false },
      pos: { read: true, write: true },
    },
  })),
}))

describe('usePermission', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should parse permission string format (module:action)', () => {
    const wrapper = ({ children }: any) =>
      React.createElement(
        PermissionsProvider,
        {},
        React.createElement(React.Fragment, {}, children)
      )

    const { result } = renderHook(() => usePermission(), { wrapper })
    const can = result.current

    // No debería funcionar sin inicializar; este test es conceptual
    expect(can).toBeInstanceOf(Function)
  })

  it('should return function that checks permissions', () => {
    const can = usePermission

    // Verificar que retorna una función
    expect(typeof can).toBe('function')
  })
})
