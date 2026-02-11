import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'
import ProtectedRoute from '../ProtectedRoute'

/**
 * Tests para ProtectedRoute component
 *
 * NOTA: Tests básicos. Requieren mock de PermissionsContext.
 */

// Mock de usePermission
vi.mock('../../hooks/usePermission', () => ({
  usePermission: () => {
    return (permission: string) => {
      // Simulación: solo "billing:create" está permitido
      return permission === 'billing:create'
    }
  },
}))

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render children when user has permission', () => {
    render(
      <ProtectedRoute permission="billing:create">
        <div data-testid="content">Protected Content</div>
      </ProtectedRoute>
    )

    expect(screen.getByTestId('content')).toBeInTheDocument()
  })

  it('should render fallback when user does not have permission', () => {
    render(
      <ProtectedRoute permission="usuarios:delete" fallback={<div data-testid="fallback">No Access</div>}>
        <div data-testid="content">Protected Content</div>
      </ProtectedRoute>
    )

    expect(screen.getByTestId('fallback')).toBeInTheDocument()
    expect(screen.queryByTestId('content')).not.toBeInTheDocument()
  })

  it('should render default unauthorized message when no fallback provided', () => {
    render(
      <ProtectedRoute permission="usuarios:delete">
        <div data-testid="content">Protected Content</div>
      </ProtectedRoute>
    )

    expect(screen.getByText('No autorizado')).toBeInTheDocument()
    expect(screen.queryByTestId('content')).not.toBeInTheDocument()
  })
})
