import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { apiFetch } from '../lib/http'
import { initElectric, setupOnlineSync } from '../lib/electric'
import { TOKEN_KEY } from '../constants/storage'
import { PermissionsProvider } from '../contexts/PermissionsContext'

type LoginBody = { identificador: string; password: string }
type LoginResponse = { access_token: string; token_type: 'bearer'; scope?: string }
type MeCompany = { user_id: string; username?: string; tenant_id: string; empresa_slug?: string; es_admin_empresa?: boolean; roles?: string[] }

type AuthContextType = {
  token: string | null
  loading: boolean
  profile: MeCompany | null
  brand: string
  login: (body: LoginBody) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<boolean>
}

const AuthContext = createContext<AuthContextType | null>(null)
const EXP_SKEW_MS = 60_000 // renew/expire 1 min before JWT exp

export const AuthProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem(TOKEN_KEY))
  const [loading, setLoading] = useState(true)
  const [profile, setProfile] = useState<MeCompany | null>(null)
  const expiryTimer = useRef<number | null>(null)
  const isUnauthorized = (e: any) => e?.status === 401 || e?.response?.status === 401

  const getTokenExpiryMs = (tok: string | null): number | null => {
    if (!tok) return null
    const [, payload] = tok.split('.')
    if (!payload) return null
    try {
      const json = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')))
      return typeof json?.exp === 'number' ? json.exp * 1000 : null
    } catch {
      return null
    }
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
              // Limpia el hash para no dejar el token en la URL
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

             // Initialize ElectricSQL for offline sync
             if (me?.tenant_id) {
               try {
                 await initElectric(me.tenant_id)
                 setupOnlineSync(me.tenant_id)
               } catch (error) {
                 console.warn('ElectricSQL init failed:', error)
               }
             }
          } else {
            clear()
          }
        } catch (e: any) {
          if (isUnauthorized(e)) {
            clear()
          } else {
            throw e
          }
        }
      } finally {
        setLoading(false)
      }
    })()
  // eslint-disable-next-line react-hooks/exhaustive-deps
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
          { method: 'POST' } as any
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

  async function loadMe(tok: string) {
    const me = await apiFetch<MeCompany>('/api/v1/me/tenant', { headers: { Authorization: `Bearer ${tok}` }, retryOn401: false })
    setProfile(me)
  }

  function clear() {
    setToken(null)
    setProfile(null)
    sessionStorage.removeItem(TOKEN_KEY)
    try { localStorage.removeItem('authToken') } catch {}
    if (expiryTimer.current) window.clearTimeout(expiryTimer.current)
  }

  const scheduleExpiryWatch = (tok: string | null) => {
    if (expiryTimer.current) window.clearTimeout(expiryTimer.current)
    const expMs = getTokenExpiryMs(tok)
    if (!expMs) return
    const now = Date.now()
    const delay = Math.max(expMs - now - EXP_SKEW_MS, 0)
    expiryTimer.current = window.setTimeout(async () => {
      const ok = await refresh()
      if (!ok) clear()
    }, delay)
  }

  const login = async (body: LoginBody) => {
    const data = await apiFetch<LoginResponse>('/api/v1/tenant/auth/login', { method: 'POST', body: JSON.stringify(body), retryOn401: false })
    setToken(data.access_token)
    sessionStorage.setItem(TOKEN_KEY, data.access_token)
    try { localStorage.setItem('authToken', data.access_token) } catch {}
    await loadMe(data.access_token)
    scheduleExpiryWatch(data.access_token)
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
      scheduleExpiryWatch(t)
      return true
    }
    return false
  }

  useEffect(() => {
    scheduleExpiryWatch(token)
    return () => {
      if (expiryTimer.current) window.clearTimeout(expiryTimer.current)
    }
  }, [token])

  const value = useMemo(() => ({ token, loading, profile, login, logout, brand: 'Empresa', refresh }), [token, loading, profile])
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
