import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import type { MeCompany } from '../auth/AuthContext'
import { apiFetch } from '../lib/http'

type MeCompanyExtended = MeCompany & {
  is_company_admin?: boolean
  is_admin_empresa?: boolean
}

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
  permisos: PermissionDict
  hasPermission: (actionOrModule: string, action?: string) => boolean
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

const PermissionsContext = createContext<PermissionsContextType | null>(null)

function splitPermissionKey(raw: string): { module: string; action: string } | null {
  const key = raw.trim()
  if (!key) return null

  const colonIndex = key.lastIndexOf(':')
  const dotIndex = key.lastIndexOf('.')
  const splitIndex = Math.max(colonIndex, dotIndex)

  if (splitIndex <= 0 || splitIndex >= key.length - 1) {
    return null
  }

  return {
    module: key.slice(0, splitIndex),
    action: key.slice(splitIndex + 1),
  }
}

function normalizePermissions(raw: unknown): PermissionDict {
  if (!raw || typeof raw !== 'object') return {}

  const normalized: PermissionDict = {}

  for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      const nested = Object.entries(value as Record<string, unknown>).reduce(
        (acc, [action, allowed]) => {
          if (allowed === true) {
            acc[action] = true
          }
          return acc
        },
        {} as Record<string, boolean>
      )

      if (Object.keys(nested).length > 0) {
        normalized[key] = {
          ...(normalized[key] || {}),
          ...nested,
        }
      }
      continue
    }

    if (value !== true) continue

    const parts = splitPermissionKey(key)
    if (!parts) continue

    normalized[parts.module] = {
      ...(normalized[parts.module] || {}),
      [parts.action]: true,
    }
  }

  return normalized
}

export const PermissionsProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const { token, profile } = useAuth()
  const [permisos, setPermisos] = useState<PermissionDict>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const refetchTimeoutRef = useRef<number | null>(null)

  const parsePermisosFromToken = (tok: string | null): PermissionDict => {
    if (!tok) return {}
    try {
      const [, payload] = tok.split('.')
      if (!payload) return {}
      const json = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/'))) as Record<string, any>
      return normalizePermissions(json?.permisos || json?.permissions)
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

  const loadPermisos = async () => {
    if (!token) {
      setPermisos({})
      setError(null)
      return
    }

    // Si el profile del AuthContext ya tiene permisos, los usamos directamente
    // evitando una llamada extra a /me/tenant
    const extProfile = profile as MeCompanyExtended | null
    const profilePermisos = extProfile?.permisos || extProfile?.permissions
    const fromProfile = normalizePermissions(profilePermisos)
    if (Object.keys(fromProfile).length > 0) {
      setPermisos(fromProfile)
      return
    }

    try {
      setLoading(true)
      setError(null)

      const meData = (await apiFetch('/api/v1/me/tenant', { retryOn401: false })) as Record<string, any>
      const normalized = normalizePermissions(meData?.permisos || meData?.permissions)

      if (Object.keys(normalized).length > 0) {
        setPermisos(normalized)
      } else {
        setPermisos(parsePermisosFromToken(token))
      }
    } catch (e: any) {
      setPermisos(parsePermisosFromToken(token))
      if (e?.status !== 401) {
        setError(`Error cargando permisos: ${e?.message || 'desconocido'}`)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPermisos()
  }, [token, profile])

  const tokenPayload = useMemo(() => parseTokenPayload(token), [token])
  const extProfile = profile as MeCompanyExtended | null
  const isCompanyAdmin =
    Boolean(profile?.es_admin_empresa) ||
    Boolean(extProfile?.is_company_admin) ||
    Boolean(extProfile?.is_admin_empresa) ||
    Boolean(tokenPayload?.es_admin_empresa) ||
    Boolean(tokenPayload?.is_company_admin) ||
    Boolean(tokenPayload?.is_admin_empresa)

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

  const hasPermission = (actionOrModule: string, action?: string): boolean => {
    if (isCompanyAdmin) {
      return true
    }

    let module: string
    let actionName: string

    if (action !== undefined) {
      module = actionOrModule
      actionName = action
    } else {
      const parts = splitPermissionKey(actionOrModule)
      if (parts) {
        module = parts.module
        actionName = parts.action
      } else {
        module = actionOrModule
        actionName = 'read'
      }
    }

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
