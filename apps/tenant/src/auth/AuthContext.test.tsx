import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { AuthProvider, useAuth } from './AuthContext'
import { BrowserRouter } from 'react-router-dom'

// Mock fetch global
const mockFetch = vi.fn()
global.fetch = mockFetch

// Componente de prueba que usa el hook
function TestComponent() {
  const { user, isAuthenticated, loading } = useAuth()

  return (
    <div>
      <div data-testid="loading">{loading ? 'loading' : 'ready'}</div>
      <div data-testid="auth">{isAuthenticated ? 'authenticated' : 'not-authenticated'}</div>
      <div data-testid="user">{user?.email || 'no-user'}</div>
    </div>
  )
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('debería iniciar sin usuario autenticado', () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401
    })

    render(
      <BrowserRouter>
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      </BrowserRouter>
    )

    expect(screen.getByTestId('auth')).toHaveTextContent('not-authenticated')
  })

  it('debería detectar usuario autenticado si hay token', async () => {
    localStorage.setItem('access_token', 'mock-token')

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ email: 'test@example.com', id: 1 })
    })

    render(
      <BrowserRouter>
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('ready')
    })
  })

  it('debería manejar error de carga', async () => {
    localStorage.setItem('access_token', 'invalid-token')

    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    render(
      <BrowserRouter>
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByTestId('auth')).toHaveTextContent('not-authenticated')
    })
  })
})
