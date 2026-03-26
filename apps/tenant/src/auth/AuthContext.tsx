import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../lib/http'
import { TOKEN_KEY } from '../constants/storage'
import { PermissionsProvider } from '../contexts/PermissionsContext'
import {
  saveCredentialsForOffline,
  saveOfflineSessionSnapshot,
  verifyOfflineCredentials,
  getOfflineProfile,
  getOfflineToken,
  clearOfflineSessionSnapshot,
  isOfflineSession,
  markOfflineSession,
  markOnlineSession,
} from '../lib/offlineAuth'

type LoginBody = { identificador: string; password: string }
type LoginScope = 'tenant' | 'admin'
type LoginResponse = { access_token: string; token_type: 'bearer'; scope?: LoginScope }
type LoginResult = { scope: LoginScope; accessToken: string }
type MeCompany = {
  user_id: string
  username?: string
  tenant_id: string
  empresa_slug?: string
  es_admin_empresa?: boolean
  roles?: string[]
  base_currency?: string
  permisos?: Record<string, unknown>
  permissions?: Record<string, unknown>
}
export type { MeCompany }

type AuthContextType = {
  token: string | null
  loading: boolean
  profile: MeCompany | null
  brand: string
  isOffline: boolean
  login: (body: LoginBody) => Promise<LoginResult>
  logout: () => Promise<void>
  refresh: () => Promise<boolean>
}

const AuthContext = createContext<AuthContextType | null>(null)
const EXP_SKEW_MS = 60_000

export const AuthProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem(TOKEN_KEY))
  const [loading, setLoading] = useState(true)
  const [profile, setProfile] = useState<MeCompany | null>(null)
  const [offlineMode, setOfflineMode] = useState(() => isOfflineSession())
  const isUnauthorized = (e: any) => e?.status === 401 || e?.response?.status === 401

  const restoreOfflineSession = async () => {
    const offlineProfile = await getOfflineProfile()
    const offlineToken = await getOfflineToken()
    if (!offlineProfile || !offlineToken) return false

    setToken(offlineToken)
    sessionStorage.setItem(TOKEN_KEY, offlineToken)
    setProfile(offlineProfile as MeCompany)
    markOfflineSession()
    setOfflineMode(true)
    return true
  }

  const parseJwtPayload = (tok: string | null): Record<string, any> | null => {
    if (!tok) return null
    const parts = tok.split('.')
    if (parts.length < 2) return null
    let base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    while (base64.length % 4 !== 0) base64 += '='
    try {
      return JSON.parse(atob(base64))
    } catch {
      return null
    }
  }

  const getTokenExpiryMs = (tok: string | null): number | null => {
    const payload = parseJwtPayload(tok)
    return typeof payload?.exp === 'number' ? payload.exp * 1000 : null
  }

  useEffect(() => {
    ;(async () => {
      try {
        if (!token && typeof window !== 'undefined') {
          try {
            const hash = window.location.hash || ''
            const match = hash.match(/[#&]access_token=([^&]+)/)
            if (match?.[1]) {
              const hashToken = decodeURIComponent(match[1])
              sessionStorage.setItem(TOKEN_KEY, hashToken)
              try { localStorage.setItem('authToken', hashToken) } catch {}
              try {
                history.replaceState(null, document.title, window.location.pathname + window.location.search)
              } catch {}
            }
          } catch {}
        }

        if (typeof navigator !== 'undefined' && navigator.onLine === false) {
          const restored = await restoreOfflineSession()
          if (restored) return
        }

        const currentToken = token ?? sessionStorage.getItem(TOKEN_KEY) ?? (await refreshOnce())
        try {
          if (!currentToken) {
            clear()
            return
          }

          setToken(currentToken)
          sessionStorage.setItem(TOKEN_KEY, currentToken)
          const me = await apiFetch<MeCompany>('/api/v1/me/tenant', {
            headers: { Authorization: `Bearer ${currentToken}` },
            retryOn401: false,
          })
          setProfile(me)
          saveOfflineSessionSnapshot(currentToken, me).catch(() => {})
          markOnlineSession()
          setOfflineMode(false)
        } catch (error: any) {
          if (isUnauthorized(error)) {
            clear()
            return
          }

          const restored = await restoreOfflineSession()
          if (restored) {
            console.log('[auth] Offline fallback loaded cached profile')
          } else {
            clear()
          }
        }
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  useEffect(() => {
    const handler = () => clear()
    window.addEventListener('tenant-auth-expired', handler as EventListener)
    return () => window.removeEventListener('tenant-auth-expired', handler as EventListener)
  }, [])

  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent).detail as { tokenKey?: string } | undefined
      if (!detail || detail.tokenKey === TOKEN_KEY) {
        clear()
      }
    }
    window.addEventListener('auth-expired', handler as EventListener)
    return () => window.removeEventListener('auth-expired', handler as EventListener)
  }, [])

  let inflightRefresh: Promise<string | null> | null = null
  async function refreshOnce(): Promise<string | null> {
    if (inflightRefresh) return inflightRefresh
    inflightRefresh = (async () => {
      try {
        const data = await apiFetch<{ access_token?: string }>('/api/v1/tenant/auth/refresh', {
          method: 'POST',
          retryOn401: false,
        } as any)
        return data?.access_token ?? null
      } catch {
        return null
      } finally {
        inflightRefresh = null
      }
    })()
    return inflightRefresh
  }

  async function loadMe(tok: string): Promise<MeCompany> {
    const me = await apiFetch<MeCompany>('/api/v1/me/tenant', {
      headers: { Authorization: `Bearer ${tok}` },
      retryOn401: false,
    })
    setProfile(me)
    saveOfflineSessionSnapshot(tok, me).catch(() => {})
    return me
  }

  function clear() {
    setToken(null)
    setProfile(null)
    setOfflineMode(false)
    markOnlineSession()
    sessionStorage.removeItem(TOKEN_KEY)
    try { localStorage.removeItem('authToken') } catch {}
  }

  const ensureTokenStillValid = async () => {
    if (offlineMode) return
    const expMs = getTokenExpiryMs(token)
    if (!expMs) return
    if (Date.now() < expMs - EXP_SKEW_MS) return
    const ok = await refresh()
    if (!ok) clear()
  }

  const login = async (body: LoginBody) => {
    try {
      const data = await apiFetch<LoginResponse>('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify(body),
        retryOn401: false,
      })
      const scope: LoginScope = data.scope === 'admin' ? 'admin' : 'tenant'
      if (scope === 'admin') {
        clear()
        return { scope, accessToken: data.access_token }
      }

      setToken(data.access_token)
      sessionStorage.setItem(TOKEN_KEY, data.access_token)
      try { localStorage.setItem('authToken', data.access_token) } catch {}
      const me = await loadMe(data.access_token)
      markOnlineSession()
      setOfflineMode(false)
      saveCredentialsForOffline(body.identificador, body.password, data.access_token, me).catch(() => {})
      return { scope, accessToken: data.access_token }
    } catch (error: any) {
      if (!navigator.onLine || error?.code === 'ERR_NETWORK' || error?.message?.includes('fetch')) {
        const offlineResult = await verifyOfflineCredentials(body.identificador, body.password)
        if (offlineResult) {
          setToken(offlineResult.token)
          sessionStorage.setItem(TOKEN_KEY, offlineResult.token)
          setProfile(offlineResult.profile as MeCompany)
          markOfflineSession()
          setOfflineMode(true)
          console.log('[auth] Offline login successful')
          return { scope: 'tenant' as LoginScope, accessToken: offlineResult.token }
        }
      }
      throw error
    }
  }

  const logout = async () => {
    try { await apiFetch('/api/v1/tenant/auth/logout', { method: 'POST', retryOn401: false }) } catch {}
    clearOfflineSessionSnapshot().catch(() => {})
    clear()
  }

  const refresh = async () => {
    const refreshedToken = await refreshOnce()
    if (refreshedToken) {
      setToken(refreshedToken)
      sessionStorage.setItem(TOKEN_KEY, refreshedToken)
      try { localStorage.setItem('authToken', refreshedToken) } catch {}
      if (profile) saveOfflineSessionSnapshot(refreshedToken, profile).catch(() => {})
      return true
    }
    return false
  }

  useEffect(() => {
    const handleOnline = async () => {
      if (!offlineMode || !token) return
      try {
        await loadMe(token)
        markOnlineSession()
        setOfflineMode(false)
        console.log('[auth] Reconnected and session validated online')
      } catch {
        const ok = await refresh()
        if (ok) {
          markOnlineSession()
          setOfflineMode(false)
        }
      }
    }
    window.addEventListener('online', handleOnline)
    return () => window.removeEventListener('online', handleOnline)
  }, [offlineMode, token, profile])

  useEffect(() => {
    const onVisibility = () => {
      if (document.visibilityState === 'visible') {
        void ensureTokenStillValid()
      }
    }
    window.addEventListener('focus', onVisibility)
    document.addEventListener('visibilitychange', onVisibility)
    return () => {
      window.removeEventListener('focus', onVisibility)
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [token, offlineMode, profile])

  const value = useMemo(
    () => ({ token, loading, profile, login, logout, brand: 'Empresa', isOffline: offlineMode, refresh }),
    [token, loading, profile, offlineMode]
  )

  return (
    <AuthContext.Provider value={value}>
      <PermissionsProvider>{children}</PermissionsProvider>
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
