import React from 'react'

export type PermisoGuardProps = {
  permiso: string
  permisos: Record<string, boolean>
  fallback?: React.ReactNode
  children: React.ReactNode
}

export function PermisoGuard({ permiso, permisos, fallback = null, children }: PermisoGuardProps) {
  if (!permisos?.[permiso]) return <>{fallback}</>
  return <>{children}</>
}
