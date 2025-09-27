// AuthContext.tsx
import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { createSharedClient } from '@shared'

const api = createSharedClient({
  baseURL: '/api',
  tokenKey: 'access_token_admin',
  refreshPath: '/v1/admin/auth/refresh',
  csrfPath: '/v1/admin/auth/csrf',
  authExemptSuffixes: ['/v1/admin/auth/login', '/v1/admin/auth/refresh', '/v1/admin/auth/logout', '/v1/admin/auth/csrf']
})

type LoginBody = { identificador: string; password: string }
type LoginResponse = { access_token: string; token_type: 'bearer'; scope?: string }
type MeAdmin = { user_id: string; is_superadmin?: boolean; user_type?: string }

type AuthContextType = {
  token: string | null
  loading: boolean
  profile: MeAdmin | null
  brand: string
  login: (body: LoginBody) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<boolean>
}

const AuthContext = createContext<AuthContextType | null>(null)

export const AuthProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem('access_token_admin'))
  const [loading, setLoading] = useState(true)
  const [profile, setProfile] = useState<MeAdmin | null>(null)

  const tokenRef = useRef<string | null>(token)
  useEffect(() => { tokenRef.current = token }, [token])

  // Sincroniza storage con token
  useEffect(() => {
    if (token) sessionStorage.setItem('access_token_admin', token)
    else sessionStorage.removeItem('access_token_admin')
  }, [token])

  async function loadMeWith(accessTok: string) {
    try {
      const r = await api.get<MeAdmin>('/v1/me/admin')
      return r.data
    } catch (e: any) {
      if (e?.status === 401) {
        await new Promise(r => setTimeout(r, 200))
        const r2 = await api.get<MeAdmin>('/v1/me/admin')
        return r2.data
      }
      throw e
    }
  }

  useEffect(() => {
    (async () => {
      try {
        // Handoff hash access token
        try {
          const hash = (typeof window !== 'undefined' ? window.location.hash : '') || ''
          if (hash.startsWith('#')) {
            const p = new URLSearchParams(hash.slice(1))
            const tHash = p.get('access_token') || p.get('access_token_admin')
            if (tHash && !sessionStorage.getItem('access_token_admin')) {
              sessionStorage.setItem('access_token_admin', tHash)
              setToken(tHash)
              if (typeof window !== 'undefined' && window.history?.replaceState) {
                const url = window.location.pathname + window.location.search
                window.history.replaceState({}, document.title, url)
              }
            }
          }
        } catch {}

        const t = tokenRef.current ?? (await refreshOnce())
        if (t) {
          sessionStorage.setItem('access_token_admin', t)
          setToken(t)
          const me = await loadMeWith(t)
          setProfile(me)
        } else {
          clear()
        }
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  async function refreshOnce(): Promise<string | null> {
    try {
      const r = await api.post<{ access_token?: string }>('/v1/admin/auth/refresh')
      return r.data?.access_token ?? null
    } catch {
      return null
    }
  }

  function clear() {
    setToken(null)
    setProfile(null)
    sessionStorage.removeItem('access_token_admin')
  }

  const login = async (body: LoginBody) => {
    try { await api.get('/v1/admin/auth/csrf') } catch {}
    const r = await api.post<LoginResponse>('/v1/admin/auth/login', { identificador: body.identificador.trim(), password: body.password })
    const data = r.data
    setToken(data.access_token)
    sessionStorage.setItem('access_token_admin', data.access_token)
    const me = await loadMeWith(data.access_token)
    setProfile(me)
  }

  const logout = async () => {
    try { await api.post('/v1/admin/auth/logout') } catch {}
    clear()
  }

  const refresh = async () => {
    const t = await refreshOnce()
    if (t) {
      setToken(t)
      sessionStorage.setItem('access_token_admin', t)
      return true
    }
    return false
  }

  const value = useMemo(
    () => ({ token, loading, profile, login, logout, brand: 'Admin', refresh }),
    [token, loading, profile, logout, refresh] as any
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
