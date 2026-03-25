import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { apiFetch } from '../lib/http'
import { TOKEN_KEY } from '../constants/storage'
import { PermissionsProvider } from '../contexts/PermissionsContext'
import {
  saveCredentialsForOffline,
  verifyOfflineCredentials,
  getOfflineProfile,
  getOfflineToken,
  clearOfflineCredentials,
  isOfflineSession,
  markOfflineSession,
  markOnlineSession,
} from '../lib/offlineAuth'

type LoginBody = { identificador: string; password: string }
type LoginScope = 'tenant' | 'admin'
type LoginResponse = { access_token: string; token_type: 'bearer'; scope?: LoginScope }
type LoginResult = { scope: LoginScope; accessToken: string }
type MeCompany = { user_id: string; username?: string; tenant_id: string; empresa_slug?: string; es_admin_empresa?: boolean; roles?: string[]; base_currency?: string; permisos?: Record<string, unknown>; permissions?: Record<string, unknown> }
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
const EXP_SKEW_MS = 60_000 // renew/expire 1 min before JWT exp

export const AuthProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem(TOKEN_KEY))
  const [loading, setLoading] = useState(true)
  const [profile, setProfile] = useState<MeCompany | null>(null)
  const [offlineMode, setOfflineMode] = useState(() => isOfflineSession())
  const isUnauthorized = (e: any) => e?.status === 401 || e?.response?.status === 401

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
    (async () => {
      try {
        // Soporte magic-link: #access_token=...
        if (!token && typeof window !== 'undefined') {
          try {
            const hash = window.location.hash || ''
            const m = hash.match(/[#&]access_token=([^&]+)/)
            if (m && m[1]) {
              const tok = decodeURIComponent(m[1])
              sessionStorage.setItem(TOKEN_KEY, tok)
              try { localStorage.setItem('authToken', tok) } catch {}
              try { history.replaceState(null, document.title, window.location.pathname + window.location.search) } catch {}
            }
            } catch {}
            }
            const t = token ?? sessionStorage.getItem(TOKEN_KEY) ?? (await refreshOnce())
        try {
          if (t) {
            setToken(t)
            sessionStorage.setItem(TOKEN_KEY, t)
            const me = await apiFetch<MeCompany>('/api/v1/me/tenant', { headers: { Authorization: `Bearer ${t}` }, retryOn401: false })
            setProfile(me)
            markOnlineSession()
            setOfflineMode(false)
          } else {
            clear()
          }
        } catch (e: any) {
          if (isUnauthorized(e)) {
            clear()
          } else {
            // Network error — try offline fallback
            const offlineProfile = await getOfflineProfile()
            const offlineToken = await getOfflineToken()
            if (offlineProfile && offlineToken) {
              setToken(offlineToken)
              sessionStorage.setItem(TOKEN_KEY, offlineToken)
              setProfile(offlineProfile as MeCompany)
              markOfflineSession()
              setOfflineMode(true)
              console.log('[auth] Offline fallback — loaded cached profile')
            } else {
              clear()
            }
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

  // Single-flight refresh to avoid concurrent rotations
  let inflightRefresh: Promise<string | null> | null = null
  async function refreshOnce(): Promise<string | null> {
    if (inflightRefresh) return inflightRefresh
    inflightRefresh = (async () => {
      try {
        const data = await apiFetch<{ access_token?: string }>(
          '/api/v1/tenant/auth/refresh',
          { method: 'POST', retryOn401: false } as any
        )
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
    const me = await apiFetch<MeCompany>('/api/v1/me/tenant', { headers: { Authorization: `Bearer ${tok}` }, retryOn401: false })
    setProfile(me)
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
      // Cache credentials for offline login
      saveCredentialsForOffline(body.identificador, body.password, data.access_token, me).catch(() => {})
      return { scope, accessToken: data.access_token }
    } catch (e: any) {
      // Network error — attempt offline login
      if (!navigator.onLine || e?.code === 'ERR_NETWORK' || e?.message?.includes('fetch')) {
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
      throw e
    }
  }

  const logout = async () => {
    try { await apiFetch('/api/v1/tenant/auth/logout', { method: 'POST', retryOn401: false }) } catch {}
    clear()
  }

  const refresh = async () => {
    const t = await refreshOnce()
    if (t) {
      setToken(t)
      sessionStorage.setItem(TOKEN_KEY, t)
      try { localStorage.setItem('authToken', t) } catch {}
      return true
    }
    return false
  }

  // Re-validate when coming back online from an offline session
  useEffect(() => {
    const handleOnline = async () => {
      if (!offlineMode || !token) return
      try {
        const me = await loadMe(token)
        markOnlineSession()
        setOfflineMode(false)
        console.log('[auth] Reconnected — session validated online')
      } catch {
        // Token might be expired — try refresh
        const ok = await refresh()
        if (ok) {
          markOnlineSession()
          setOfflineMode(false)
        }
      }
    }
    window.addEventListener('online', handleOnline)
    return () => window.removeEventListener('online', handleOnline)
  }, [offlineMode, token])

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
  }, [token])

  const value = useMemo(() => ({ token, loading, profile, login, logout, brand: 'Empresa', isOffline: offlineMode, refresh }), [token, loading, profile, offlineMode])
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
