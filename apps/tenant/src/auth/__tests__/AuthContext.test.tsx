/**
 * Tests para AuthContext
 * Coverage: Autenticación con cookies HttpOnly
 */
import { renderHook, act, waitFor } from '@testing-library/react'
import { AuthProvider, useAuth } from '../AuthContext'

// Mock fetch
global.fetch = jest.fn()

describe('AuthContext', () => {
  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks()
    localStorage.clear()
  })

  describe('Login', () => {
    it('should login successfully with cookies', async () => {
      // Mock successful login
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          user: {
            id: '123',
            email: 'test@example.com',
            tenant_id: 'tenant-1'
          }
        })
      })

      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AuthProvider>{children}</AuthProvider>
      )

      const { result } = renderHook(() => useAuth(), { wrapper })

      await act(async () => {
        await result.current.login('test@example.com', 'password123')
      })

      // Verificar que fetch se llamó con credentials: 'include'
      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          credentials: 'include'
        })
      )

      // Verificar que NO se guardó token en localStorage
      expect(localStorage.getItem('access_token')).toBeNull()
      expect(localStorage.getItem('refresh_token')).toBeNull()

      // Verificar que usuario está autenticado
      await waitFor(() => {
        expect(result.current.user).not.toBeNull()
      })
    })

    it('should handle login failure', async () => {
      // Mock failed login
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Invalid credentials' })
      })

      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AuthProvider>{children}</AuthProvider>
      )

      const { result } = renderHook(() => useAuth(), { wrapper })

      await act(async () => {
        try {
          await result.current.login('test@example.com', 'wrong_password')
        } catch (error) {
          // Expected error
        }
      })

      // Usuario no autenticado
      expect(result.current.user).toBeNull()
    })
  })

  describe('Logout', () => {
    it('should logout and clear cookies via backend', async () => {
      // Mock logout
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'Logged out' })
      })

      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AuthProvider>{children}</AuthProvider>
      )

      const { result } = renderHook(() => useAuth(), { wrapper })

      await act(async () => {
        await result.current.logout()
      })

      // Verificar que fetch se llamó con credentials
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/logout'),
        expect.objectContaining({
          credentials: 'include'
        })
      )

      // Usuario eliminado
      expect(result.current.user).toBeNull()
    })
  })

  describe('Protected Fetch', () => {
    it('should send cookies automatically', async () => {
      // Mock protected endpoint
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: 'protected data' })
      })

      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AuthProvider>{children}</AuthProvider>
      )

      const { result } = renderHook(() => useAuth(), { wrapper })

      await act(async () => {
        await result.current.fetchProtected('/api/v1/protected')
      })

      // Verificar que NO se agregó Authorization header
      const fetchCall = (global.fetch as jest.Mock).mock.calls[0]
      const headers = fetchCall[1]?.headers || {}
      
      expect(headers.Authorization).toBeUndefined()

      // Verificar que credentials: 'include' está presente
      expect(fetchCall[1]).toMatchObject({
        credentials: 'include'
      })
    })
  })
})
