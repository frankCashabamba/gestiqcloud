import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../lib/http'

type LoginBody = { identificador: string; password: string }
type LoginResponse = { access_token: string; token_type: 'bearer'; scope?: string }
type MeTenant = { user_id: string; tenant_id: string; empresa_slug?: string; roles?: string[] }

type AuthContextType = {
  token: string | null
  loading: boolean
  profile: MeTenant | null
  brand: string
  login: (body: LoginBody) => Promise<void>
  logout: () => Promise<void>
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

  async function refreshOnce(): Promise<string | null> {
    const res = await fetch(`/api/api/v1/tenant/auth/refresh`.replace('/api/api','/api'), { method: 'POST', credentials: 'include' })
    if (!res.ok) return null
    const data = await res.json()
    return data?.access_token ?? null
  }

  async function loadMe(tok: string) {
    const me = await apiFetch<MeTenant>('/api/v1/me/tenant', { headers: { Authorization: `Bearer ${tok}` }, retryOn401: false })
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
    try { await apiFetch('/api/v1/tenant/auth/logout', { method: 'POST', retryOn401: false }) } catch {}
    clear()
  }

  const value = useMemo(() => ({ token, loading, profile, login, logout, brand: 'Empresa' }), [token, loading, profile])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
