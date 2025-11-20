import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'

type Role = 'superadmin' | 'admin_empresa' | 'usuario'

export type SecureRouteProps = {
  children: JSX.Element
  rolesPermitidos?: Role[]
  permiso?: string
  getToken: () => string | null
  decode: (t: string) => any
}

export function SecureRoute({ children, rolesPermitidos = ['superadmin', 'admin_empresa', 'usuario'], permiso, getToken, decode }: SecureRouteProps) {
  const location = useLocation()
  const token = getToken()

  if (!token) return <Navigate to="/login" replace state={{ from: location }} />

  try {
    const decoded: any = decode(token)
    const now = Math.floor(Date.now() / 1000)
    if (decoded?.exp && decoded.exp < now) return <Navigate to="/login" replace state={{ from: location }} />

    const isSuperAdmin = !!decoded?.is_superadmin
    const isAdminEmpresa = !!decoded?.es_admin_empresa
    const permisos = decoded?.permisos || {}

    let rolActual: Role = 'usuario'
    if (isSuperAdmin) rolActual = 'superadmin'
    else if (isAdminEmpresa) rolActual = 'admin_empresa'

    if (!rolesPermitidos.includes(rolActual)) return <Navigate to="/unauthorized" replace />

    if (permiso) {
      const tienePermiso = isSuperAdmin || isAdminEmpresa || permisos[permiso] || permisos['*']
      if (!tienePermiso) return <Navigate to="/unauthorized" replace />
    }

    return children
  } catch {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
}
