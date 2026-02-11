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
  /** Permiso requerido: "usuarios:create" o separado: ("usuarios", "create") */
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
        backgroundColor: '#fee2e2',
        border: '1px solid #fca5a5',
      }}
    >
      <h2 style={{ color: '#991b1b', marginBottom: '0.5rem' }}>Unauthorized</h2>
      <p style={{ color: '#7f1d1d', marginBottom: '0.5rem' }}>
        You do not have permission to access: <code>{displayPerm}</code>
      </p>
      <p style={{ color: '#7f1d1d', fontSize: '0.875rem' }}>
        Contact your administrator if you believe you should have access.
      </p>
    </div>
  )
}
