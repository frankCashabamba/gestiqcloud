import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'
import ProtectedButton from '../ProtectedButton'

/**
 * Tests para ProtectedButton component
 */

// Mock de usePermission y usePermissionLabel
vi.mock('../../hooks/usePermission', () => ({
  usePermission: () => {
    return (permission: string) => {
      return permission === 'billing:create'
    }
  },
}))

vi.mock('../../hooks/usePermissionLabel', () => ({
  usePermissionLabel: () => {
    return (permission: string) => {
      const labels: Record<string, string> = {
        'billing:create': 'Crear factura',
        'usuarios:delete': 'Eliminar usuario',
      }
      return labels[permission] || permission
    }
  },
}))

describe('ProtectedButton', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render enabled button when user has permission', () => {
    const { container } = render(
      <ProtectedButton permission="billing:create">
        Create Invoice
      </ProtectedButton>
    )

    const btn = container.querySelector('button')
    expect(btn).not.toBeDisabled()
  })

  it('should render disabled button when user does not have permission', () => {
    const { container } = render(
      <ProtectedButton permission="usuarios:delete">
        Delete User
      </ProtectedButton>
    )

    const btn = container.querySelector('button')
    expect(btn).toBeDisabled()
  })

  it('should call onClick when clicked and user has permission', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()

    const { container } = render(
      <ProtectedButton permission="billing:create" onClick={onClick}>
        Create Invoice
      </ProtectedButton>
    )

    const btn = container.querySelector('button')!
    await user.click(btn)

    expect(onClick).toHaveBeenCalled()
  })

  it('should NOT call onClick when clicked and user does not have permission', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()

    const { container } = render(
      <ProtectedButton permission="usuarios:delete" onClick={onClick}>
        Delete User
      </ProtectedButton>
    )

    const btn = container.querySelector('button')!
    await user.click(btn)

    expect(onClick).not.toHaveBeenCalled()
  })

  it('should show tooltip with permission label when disabled', () => {
    const { container } = render(
      <ProtectedButton permission="usuarios:delete">
        Delete User
      </ProtectedButton>
    )

    const btn = container.querySelector('button')!
    expect(btn.title).toContain('No tienes permiso')
  })
})
