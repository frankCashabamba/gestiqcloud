import React from 'react'
import { usePermission } from '../hooks/usePermission'

/**
 * ProtectedRoute Component
 *
 * Renderiza children si el usuario tiene el permiso requerido.
 * Si no, renderiza fallback (por defecto <Unauthorized />).
 *
 * Uso:
 *   <ProtectedRoute permission="billing:create">
 *     <BillingForm />
 *   </ProtectedRoute>
 *
 *   <ProtectedRoute
 *     permission="pos:write"
 *     fallback={<CustomAccessDenied />}
 *   >
 *     <POSManager />
 *   </ProtectedRoute>
 */

export interface ProtectedRouteProps {
  /** Permiso requerido: "users:create" o separado: ("users", "create") */
  permission: string
  /** Segundo parte del permiso si se pasa separado */
  action?: string
  /** Componente a renderizar si NO tiene permiso (default: Unauthorized) */
  fallback?: React.ReactNode
  /** Componente a renderizar si tiene permiso */
  children: React.ReactNode
}

export default function ProtectedRoute({
  permission,
  action,
  fallback,
  children,
}: ProtectedRouteProps) {
  const can = usePermission()

  if (!can(permission, action)) {
    if (fallback !== undefined) {
      return <>{fallback}</>
    }
    // Default: renderizar componente Unauthorized inline
    return <UnauthorizedDefault permission={permission} action={action} />
  }

  return <>{children}</>
}

/**
 * UnauthorizedDefault: default component when access is denied
 */
function UnauthorizedDefault({ permission, action }: { permission: string; action?: string }) {
  const displayPerm = action ? `${permission}:${action}` : permission
  return (
    <div
      style={{
        padding: '2rem',
        textAlign: 'center',
        borderRadius: '0.5rem',
        backgroundColor: 'color-mix(in srgb, var(--gc-danger) 10%, white)',
        border: '1px solid color-mix(in srgb, var(--gc-danger) 30%, white)',
      }}
    >
      <h2 style={{ color: 'var(--gc-danger)', marginBottom: '0.5rem' }}>No autorizado</h2>
      <p style={{ color: 'var(--gc-foreground)', marginBottom: '0.5rem' }}>
        No tienes permiso para acceder a: <code>{displayPerm}</code>
      </p>
      <p style={{ color: 'var(--gc-foreground)', fontSize: '0.875rem' }}>
        Contacta a tu administrador si crees que deberías tener acceso.
      </p>
    </div>
  )
}
