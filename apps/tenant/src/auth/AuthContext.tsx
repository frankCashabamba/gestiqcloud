import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../lib/http'

type LoginBody = { identificador: string; password: string }
type LoginResponse = { access_token: string; token_type: 'bearer'; scope?: string }
type MeTenant = { user_id: string; username?: string; tenant_id: string; empresa_slug?: string; es_admin_empresa?: boolean; roles?: string[] }

type AuthContextType = {
  token: string | null
  loading: boolean
  profile: MeTenant | null
  brand: string
  login: (body: LoginBody) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<boolean>
}

const AuthContext = createContext<AuthContextType | null>(null)

export const AuthProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem('access_token_tenant'))
  const [loading, setLoading] = useState(true)
  const [profile, setProfile] = useState<MeTenant | null>(null)

  useEffect(() => {
    (async () => {
      try {
        const t = token ?? (await refreshOnce())
        if (t) {
          setToken(t)
          sessionStorage.setItem('access_token_tenant', t)
          const me = await apiFetch<MeTenant>('/v1/me/tenant', { headers: { Authorization: `Bearer ${t}` }, retryOn401: false })
          setProfile(me)
        } else {
          clear()
        }
      } finally {
        setLoading(false)
      }
    })()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Single-flight refresh to avoid concurrent rotations
  let inflightRefresh: Promise<string | null> | null = null
  async function refreshOnce(): Promise<string | null> {
    if (inflightRefresh) return inflightRefresh
    inflightRefresh = (async () => {
      try {
        const data = await apiFetch<{ access_token?: string }>(
          '/v1/tenant/auth/refresh',
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
    const me = await apiFetch<MeTenant>('/v1/me/tenant', { headers: { Authorization: `Bearer ${tok}` }, retryOn401: false })
    setProfile(me)
  }

  function clear() {
    setToken(null)
    setProfile(null)
    sessionStorage.removeItem('access_token_tenant')
  }

  const login = async (body: LoginBody) => {
    const data = await apiFetch<LoginResponse>('/v1/tenant/auth/login', { method: 'POST', body: JSON.stringify(body), retryOn401: false })
    setToken(data.access_token)
    sessionStorage.setItem('access_token_tenant', data.access_token)
    await loadMe(data.access_token)
  }

  const logout = async () => {
    try { await apiFetch('/v1/tenant/auth/logout', { method: 'POST', retryOn401: false }) } catch {}
    clear()
  }

  const refresh = async () => {
    const t = await refreshOnce()
    if (t) {
      setToken(t)
      sessionStorage.setItem('access_token_tenant', t)
      return true
    }
    return false
  }

  const value = useMemo(() => ({ token, loading, profile, login, logout, brand: 'Empresa', refresh }), [token, loading, profile])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
