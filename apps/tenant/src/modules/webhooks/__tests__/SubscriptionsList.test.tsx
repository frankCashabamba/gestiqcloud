import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}))

vi.mock('../../../shared/toast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}))

vi.mock('../../../hooks/usePermission', () => ({
  usePermission: () => () => true,
}))

vi.mock('../../../hooks/usePermissionLabel', () => ({
  usePermissionLabel: () => () => 'permiso',
}))

vi.mock('@ui', () => ({
  BackButton: () => <button>Back</button>,
}))

const listMock = vi.fn()
vi.mock('../services', () => ({
  listSubscriptions: (...args: any[]) => listMock(...args),
  createSubscription: vi.fn(),
  deleteSubscription: vi.fn(),
  testSubscription: vi.fn(),
}))

import SubscriptionsList from '../SubscriptionsList'

describe('SubscriptionsList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('muestra el secret enmascarado cuando el backend devuelve secret_masked', async () => {
    listMock.mockResolvedValue([
      {
        id: 'wh-1',
        event: 'order.created',
        url: 'https://example.com/hook',
        secret_masked: '***abcd',
        active: true,
        created_at: '2025-01-01T00:00:00Z',
      },
    ])

    render(
      <MemoryRouter>
        <SubscriptionsList />
      </MemoryRouter>
    )

    await waitFor(() => expect(listMock).toHaveBeenCalled())
    const masked = await screen.findByText(/Secret:\s*\*\*\*abcd/)
    expect(masked).toBeTruthy()
  })

  it('no muestra la línea Secret cuando secret_masked es null', async () => {
    listMock.mockResolvedValue([
      {
        id: 'wh-2',
        event: 'order.created',
        url: 'https://example.com/hook',
        secret_masked: null,
        active: true,
        created_at: '2025-01-01T00:00:00Z',
      },
    ])

    render(
      <MemoryRouter>
        <SubscriptionsList />
      </MemoryRouter>
    )

    await waitFor(() => expect(listMock).toHaveBeenCalled())
    await screen.findByText('https://example.com/hook')
    expect(screen.queryByText(/Secret:/)).toBeNull()
  })
})
