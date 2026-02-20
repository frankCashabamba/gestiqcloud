import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { apiFetch } from '../lib/http'

/**
 * PermissionsContext
 *
 * Proporciona acceso a permisos granulares del usuario.
 * Estructura: { "usuarios": { "create": true, "delete": false }, "billing": { "read": true } }
 *
 * NOTA: No modifica backend existente. Lee permisos del JWT/API backend.
 */

export type PermissionDict = Record<string, Record<string, boolean>>

export type PermissionsContextType = {
  /** Permisos del usuario: {"module": {"action": true}} */
  permisos: PermissionDict
  /** Chequea si usuario tiene permiso: "usuarios:create" o ("usuarios", "create") */
  hasPermission: (actionOrModule: string, action?: string) => boolean
  /** Loading inicial de permisos */
  loading: boolean
  /** Error al cargar permisos */
  error: string | null
  /** Refetch manual de permisos */
  refetch: () => Promise<void>
}

const PermissionsContext = createContext<PermissionsContextType | null>(null)

export const PermissionsProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const { token, profile } = useAuth()
  const [permisos, setPermisos] = useState<PermissionDict>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const refetchTimeoutRef = useRef<number | null>(null)

  // Parsear permisos del JWT token (ya vienen en access_claims del backend)
  const parsePermisosFromToken = (tok: string | null): PermissionDict => {
    if (!tok) return {}
    try {
      const [, payload] = tok.split('.')
      if (!payload) return {}
      const json = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/'))) as Record<string, any>
      // El backend inyecta "permisos" en el token
      if (json?.permisos && typeof json.permisos === 'object') {
        return json.permisos as PermissionDict
      }
      return {}
    } catch {
      return {}
    }
  }

  const parseTokenPayload = (tok: string | null): Record<string, any> => {
    if (!tok) return {}
    try {
      const [, payload] = tok.split('.')
      if (!payload) return {}
      return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/'))) as Record<string, any>
    } catch {
      return {}
    }
  }

  // Cargar permisos: primero del token, luego refetch del API si es necesario
  const loadPermisos = async () => {
    if (!token) {
      setPermisos({})
      setError(null)
      return
    }

    try {
      setLoading(true)
      setError(null)

      // Intenta traer permisos frescos del API
      // (si el token está actualizado, el API devuelve permisos en la respuesta)
      const meData = (await apiFetch('/api/v1/me/tenant', { retryOn401: false })) as Record<string, any>

      if (meData?.permisos && typeof meData.permisos === 'object') {
        setPermisos(meData.permisos as PermissionDict)
      } else {
        // Fallback al token
        const fromToken = parsePermisosFromToken(token)
        setPermisos(fromToken)
      }
    } catch (e: any) {
      // Si falla API, usar token como fallback
      const fromToken = parsePermisosFromToken(token)
      setPermisos(fromToken)
      if (e?.status !== 401) {
        setError(`Error cargando permisos: ${e?.message || 'desconocido'}`)
      }
    } finally {
      setLoading(false)
    }
  }

  // Cargar permisos al cambiar token
  useEffect(() => {
    loadPermisos()
  }, [token])

  const tokenPayload = useMemo(() => parseTokenPayload(token), [token])
  const isCompanyAdmin =
    Boolean(profile?.es_admin_empresa) ||
    Boolean((profile as any)?.is_company_admin) ||
    Boolean((profile as any)?.is_admin_empresa) ||
    Boolean(tokenPayload?.es_admin_empresa) ||
    Boolean(tokenPayload?.is_company_admin) ||
    Boolean(tokenPayload?.is_admin_empresa)

  // Refetch automático cada 10 minutos (cuando hay cambios de rol)
  useEffect(() => {
    if (!token) return

    if (refetchTimeoutRef.current) {
      clearTimeout(refetchTimeoutRef.current)
    }

    refetchTimeoutRef.current = window.setTimeout(() => {
      loadPermisos()
    }, 10 * 60 * 1000)

    return () => {
      if (refetchTimeoutRef.current) {
        clearTimeout(refetchTimeoutRef.current)
      }
    }
  }, [token])

  // Chequear permisos
  const hasPermission = (actionOrModule: string, action?: string): boolean => {
    // Admin global de empresa: bypass total (profile o JWT)
    if (isCompanyAdmin) {
      return true
    }

    // Parse: "usuarios:create" o ("usuarios", "create")
    let module: string
    let actionName: string

    if (action !== undefined) {
      module = actionOrModule
      actionName = action
    } else {
      const parts = actionOrModule.split(':')
      if (parts.length === 2) {
        module = parts[0]
        actionName = parts[1]
      } else {
        // Si no tiene ":", asumir que es un módulo entero
        module = actionOrModule
        actionName = 'read' // default
      }
    }

    // Chequear en dict
    const modulePerms = permisos[module]
    if (!modulePerms || typeof modulePerms !== 'object') {
      return false
    }

    return Boolean(modulePerms[actionName] === true)
  }

  const value = useMemo(
    () => ({
      permisos,
      hasPermission,
      loading,
      error,
      refetch: loadPermisos,
    }),
    [permisos, loading, error, isCompanyAdmin]
  )

  return <PermissionsContext.Provider value={value}>{children}</PermissionsContext.Provider>
}

export function usePermissions() {
  const ctx = useContext(PermissionsContext)
  if (!ctx) {
    throw new Error('usePermissions must be used within PermissionsProvider')
  }
  return ctx
}
