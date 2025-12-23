// AuthContext.tsx
import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { createSharedClient } from '@shared'
import { registerAuthHandlers } from '../lib/http'
import { env } from '../env'

const api = createSharedClient({
    baseURL: env.apiUrl,
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

    async function loadMeProfile(token: string): Promise<MeAdmin> {
        try {
            const r = await api.get<MeAdmin>('/v1/me/admin')
            return r.data
        } catch (e: any) {
            throw e
        }
    }

    const isUnauthorized = (e: any) => e?.status === 401 || e?.response?.status === 401

    /**
     * Intenta refrescar el token usando refresh_token cookie (si disponible)
     * Solo se llama si hay credenciales válidas en el almacenamiento o cookies
     */
    async function refreshOnceIfPossible(): Promise<string | null> {
        try {
            const r = await api.post<{ access_token?: string }>('/v1/admin/auth/refresh')
            return r.data?.access_token ?? null
        } catch {
            // El refresh falló (no hay refresh_token cookie o expiró)
            return null
        }
    }

    /**
     * Extrae token de URL hash (OAuth/SSO handoff)
     */
    function extractHashToken(): string | null {
        try {
            const hash = (typeof window !== 'undefined' ? window.location.hash : '') || ''
            if (hash.startsWith('#')) {
                const p = new URLSearchParams(hash.slice(1))
                const tHash = p.get('access_token') || p.get('access_token_admin')
                if (tHash && !sessionStorage.getItem('access_token_admin')) {
                    sessionStorage.setItem('access_token_admin', tHash)
                    if (typeof window !== 'undefined' && window.history?.replaceState) {
                        const url = window.location.pathname + window.location.search
                        window.history.replaceState({}, document.title, url)
                    }
                    return tHash
                }
            }
        } catch { }
        return null
    }

    /**
     * Flujo de inicialización de autenticación:
     * 1. Intenta extraer token de URL hash (OAuth handoff)
     * 2. Usa token de sessionStorage si existe
     * 3. Solo intenta refresh si hay refresh_token cookie válida
     * 4. Si nada funciona, usuario debe iniciar sesión
     */
    useEffect(() => {
        (async () => {
            try {
                // Paso 1: Extraer token de URL hash (OAuth/SSO)
                let token = extractHashToken() ?? tokenRef.current

                // Paso 2: Intentar refresh solo si NO hay token local pero sí hay refresh_token cookie
                if (!token) {
                    const refreshedToken = await refreshOnceIfPossible()
                    if (refreshedToken) {
                        token = refreshedToken
                        sessionStorage.setItem('access_token_admin', token)
                    }
                }

                // Paso 3: Cargar perfil si tenemos un token válido
                if (token) {
                    setToken(token)
                    try {
                        const profile = await loadMeProfile(token)
                        setProfile(profile)
                    } catch (e: any) {
                        // Token inválido o expirado, limpiar sesión
                        if (isUnauthorized(e)) {
                            clear()
                        } else {
                            throw e
                        }
                    }
                } else {
                    // Sin token y sin refresh_token: usuario no autenticado
                    clear()
                }
            } finally {
                setLoading(false)
            }
        })()
    }, [])

    function clear() {
        setToken(null)
        setProfile(null)
        sessionStorage.removeItem('access_token_admin')
    }

    const login = async (body: LoginBody) => {
          try { await api.get('/v1/admin/auth/csrf') } catch { }
           const r = await api.post<LoginResponse>('/v1/admin/auth/login', { identificador: body.identificador.trim(), password: body.password })
           const data = r.data
           // ✅ Actualizar tokenRef INMEDIATAMENTE para evitar race condition en remount
           tokenRef.current = data.access_token
           setToken(data.access_token)
           sessionStorage.setItem('access_token_admin', data.access_token)
           const me = await loadMeProfile(data.access_token)
           setProfile(me)
       }

    const logout = async () => {
        try { await api.post('/v1/admin/auth/logout') } catch { }
        clear()
    }

    const refresh = async () => {
        const t = await refreshOnceIfPossible()
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

    // Bridge tokens into legacy apiFetch helper used by some services (ops.ts)
    useEffect(() => {
        registerAuthHandlers({
            getToken: () => (typeof window !== 'undefined' ? sessionStorage.getItem('access_token_admin') : null),
            setToken: (t) => {
                if (typeof window === 'undefined') return
                if (t) sessionStorage.setItem('access_token_admin', t)
                else sessionStorage.removeItem('access_token_admin')
            },
            refresh: refreshOnceIfPossible,
        })
    }, [])

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
    const ctx = useContext(AuthContext)
    if (!ctx) throw new Error('useAuth must be used within AuthProvider')
    return ctx
}
