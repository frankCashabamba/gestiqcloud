import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react'
import type { AxiosInstance } from 'axios'

export type AuthConfig = {
  api: AxiosInstance
  mePath: string
  loginPath: string
  logoutPath: string
  refreshPath: string
  storageKey: string
  brand: string
}

export function createAuth(cfg: AuthConfig) {
  type LoginBody = { identificador: string; password: string }
  type LoginResponse = { access_token: string }

  type AuthContextType = {
    token: string | null
    loading: boolean
    profile: any | null
    login: (b: LoginBody) => Promise<void>
    logout: () => Promise<void>
    refresh: () => Promise<boolean>
    brand: string
  }

  const Ctx = createContext<AuthContextType | null>(null)

  function AuthProvider({ children }: React.PropsWithChildren) {
    const [token, setToken] = useState<string | null>(() => sessionStorage.getItem(cfg.storageKey))
    const [loading, setLoading] = useState(true)
    const [profile, setProfile] = useState<any | null>(null)
    const tokRef = useRef(token)
    useEffect(() => { tokRef.current = token }, [token])

    async function refreshOnce(): Promise<string | null> {
      try {
        const res = await cfg.api.post<{ access_token?: string }>(cfg.refreshPath, undefined, { retryOn401: false } as any)
        return res.data?.access_token ?? null
      } catch { return null }
    }

    async function loadMe(accessTok: string) {
      const res = await cfg.api.get(cfg.mePath, { headers: { Authorization: `Bearer ${accessTok}` }, retryOn401: false } as any)
      setProfile(res.data)
    }

    useEffect(() => {
      (async () => {
        try {
          const t = tokRef.current ?? (await refreshOnce())
          if (t) { setToken(t); sessionStorage.setItem(cfg.storageKey, t); await loadMe(t) }
          else { clear() }
        } finally { setLoading(false) }
      })()
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    function clear() {
      setToken(null); setProfile(null); sessionStorage.removeItem(cfg.storageKey)
    }

    const login = async (b: LoginBody) => {
      const { data } = await cfg.api.post<LoginResponse>(cfg.loginPath, { identificador: b.identificador.trim(), password: b.password }, { retryOn401: false } as any)
      setToken(data.access_token); sessionStorage.setItem(cfg.storageKey, data.access_token)
      await loadMe(data.access_token)
    }

    const logout = async () => { try { await cfg.api.post(cfg.logoutPath, undefined, { retryOn401: false } as any) } catch {} ; clear() }
    const refresh = async () => { const t = await refreshOnce(); if (t) { setToken(t); sessionStorage.setItem(cfg.storageKey, t); return true } ; return false }

    const value = useMemo(() => ({ token, loading, profile, login, logout, brand: cfg.brand, refresh }), [token, loading, profile])
    return <Ctx.Provider value={value}>{children}</Ctx.Provider>
  }

  const useAuth = () => {
    const ctx = useContext(Ctx)
    if (!ctx) throw new Error('useAuth must be used within AuthProvider')
    return ctx
  }

  return { AuthProvider, useAuth }
}

