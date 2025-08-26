// AuthContext.tsx
import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { apiFetch, registerAuthHandlers } from '../lib/http'

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

  // Mantén el token en un ref para evitar carreras
  const tokenRef = useRef<string | null>(token)
  useEffect(() => { tokenRef.current = token }, [token])

  // Registra los handlers UNA vez
  useEffect(() => {
    registerAuthHandlers({
      getToken: () => tokenRef.current,
      setToken: (t) => {
        setToken(t)
        if (t) sessionStorage.setItem('access_token_admin', t)
        else sessionStorage.removeItem('access_token_admin')
      },
      refresh: refreshOnce, // usará el endpoint de admin
    })
  }, [])

  // helper: carga /me con el token pasado (y un reintento corto si justo se emitió)
  async function loadMeWith(accessTok: string) {
    try {
      return await apiFetch<MeAdmin>('/v1/me/admin', { authToken: accessTok } as any)
    } catch (e: any) {
      if (e?.status === 401) {
        await new Promise(r => setTimeout(r, 200))
        return await apiFetch<MeAdmin>('/v1/me/admin', { authToken: accessTok, retryOn401: false } as any)
      }
      throw e
    }
  }

  // Al montar: intenta recuperar sesión y carga /me
  useEffect(() => {
    (async () => {
      try {
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function refreshOnce(): Promise<string | null> {
    try {
      const data = await apiFetch<{ access_token?: string }>('/v1/admin/auth/refresh', { // ✅ ADMIN
        method: 'POST',
        retryOn401: false,
      } as any)
      return data?.access_token ?? null
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
    // (opcional) precalienta cookie CSRF específica de admin
    try { await apiFetch('/v1/admin/auth/csrf', { retryOn401: false } as any) } catch {}

    const data = await apiFetch<LoginResponse>('/v1/admin/auth/login', {
      method: 'POST',
      body: JSON.stringify({ identificador: body.identificador.trim(), password: body.password }),
      retryOn401: false,
      headers: { 'Content-Type': 'application/json' },
    } as any)

    setToken(data.access_token)
    sessionStorage.setItem('access_token_admin', data.access_token)

    const me = await loadMeWith(data.access_token) // ✅ primer /me con token explícito
    setProfile(me)
  }

  const logout = async () => {
    try { await apiFetch('/v1/admin/auth/logout', { method: 'POST', retryOn401: false } as any) } catch {} // ✅ ADMIN
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
    [token, loading, profile, login, logout, refresh] as any
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
