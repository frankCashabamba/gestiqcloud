/**
 * Tests para AuthContext
 * Coverage: login, logout, profile, initial state
 */
import { renderHook, act, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

// ── Mocks ────────────────────────────────────────────────────────────────────

// Mock apiFetch from lib/http (paths relative to test file)
const apiFetchMock = vi.fn()
vi.mock('../../lib/http', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}))

// Mock offlineAuth helpers
vi.mock('../../lib/offlineAuth', () => ({
  saveCredentialsForOffline: vi.fn().mockResolvedValue(undefined),
  saveOfflineSessionSnapshot: vi.fn().mockResolvedValue(undefined),
  verifyOfflineCredentials: vi.fn().mockResolvedValue(null),
  getOfflineProfile: vi.fn().mockResolvedValue(null),
  getOfflineToken: vi.fn().mockResolvedValue(null),
  clearOfflineSessionSnapshot: vi.fn().mockResolvedValue(undefined),
  isOfflineSession: vi.fn().mockReturnValue(false),
  markOfflineSession: vi.fn(),
  markOnlineSession: vi.fn(),
}))

// Mock PermissionsContext so it just renders children
vi.mock('../../contexts/PermissionsContext', () => ({
  PermissionsProvider: ({ children }: { children: React.ReactNode }) => children,
}))

// Mock constants/storage
vi.mock('../../constants/storage', () => ({
  TOKEN_KEY: 'access_token_tenant',
  AUTH_FALLBACK_TOKEN_KEY: 'authToken',
}))

import React from 'react'
import { AuthProvider, useAuth } from '../AuthContext'

// ── Helpers ──────────────────────────────────────────────────────────────────

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
)

/** Wait until loading finishes after initial mount. */
async function renderAndWaitForLoad() {
  const hook = renderHook(() => useAuth(), { wrapper })
  await waitFor(() => {
    expect(hook.result.current.loading).toBe(false)
  })
  return hook
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    // Init-phase calls (refresh + me) reject so loading finishes quickly.
    apiFetchMock.mockRejectedValue(new Error('no session'))
  })

  describe('initial state', () => {
    it('profile is null after loading completes with no session', async () => {
      const { result } = await renderAndWaitForLoad()

      expect(result.current.profile).toBeNull()
      expect(result.current.token).toBeNull()
      expect(result.current.loading).toBe(false)
    })
  })

  describe('login', () => {
    it('should login successfully and set profile', async () => {
      const { result } = await renderAndWaitForLoad()

      const fakeToken = 'jwt.token.here'
      const fakeProfile = {
        user_id: '123',
        tenant_id: 'tenant-1',
        username: 'test@example.com',
      }

      apiFetchMock
        .mockResolvedValueOnce({
          access_token: fakeToken,
          token_type: 'bearer',
          scope: 'tenant',
        })
        .mockResolvedValueOnce(fakeProfile)

      await act(async () => {
        const loginResult = await result.current.login({
          identificador: 'test@example.com',
          password: 'password123',
        })
        expect(loginResult).toEqual({ scope: 'tenant', accessToken: fakeToken })
      })

      expect(apiFetchMock).toHaveBeenCalledWith(
        '/api/v1/auth/login',
        expect.objectContaining({ method: 'POST' }),
      )

      await waitFor(() => {
        expect(result.current.profile).toEqual(fakeProfile)
      })
      expect(result.current.token).toBe(fakeToken)
    })

    it('should handle login failure', async () => {
      const { result } = await renderAndWaitForLoad()

      apiFetchMock.mockRejectedValueOnce(
        Object.assign(new Error('Invalid credentials'), { status: 401 }),
      )

      await act(async () => {
        await expect(
          result.current.login({ identificador: 'bad@example.com', password: 'wrong' }),
        ).rejects.toThrow('Invalid credentials')
      })

      expect(result.current.profile).toBeNull()
    })
  })

  describe('logout', () => {
    it('should logout, call backend, and clear profile', async () => {
      const { result } = await renderAndWaitForLoad()

      apiFetchMock
        .mockResolvedValueOnce({ access_token: 'tok', token_type: 'bearer', scope: 'tenant' })
        .mockResolvedValueOnce({ user_id: 'u1', tenant_id: 't1' })

      await act(async () => {
        await result.current.login({ identificador: 'user', password: 'pass' })
      })

      apiFetchMock.mockResolvedValueOnce(undefined)

      await act(async () => {
        await result.current.logout()
      })

      expect(apiFetchMock).toHaveBeenCalledWith(
        '/api/v1/tenant/auth/logout',
        expect.objectContaining({ method: 'POST' }),
      )

      expect(result.current.profile).toBeNull()
      expect(result.current.token).toBeNull()
    })
  })
})
