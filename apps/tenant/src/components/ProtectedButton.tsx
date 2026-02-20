import React from 'react'
import { usePermission } from '../hooks/usePermission'
import { usePermissionLabel } from '../hooks/usePermissionLabel'

/**
 * ProtectedButton Component
 *
 * Renderiza un botón, deshabilitado si el usuario NO tiene el permiso.
 * Muestra tooltip explicativo en hover.
 *
 * Uso:
 *   <ProtectedButton permission="billing:create" onClick={handleCreate}>
 *     Crear factura
 *   </ProtectedButton>
 *
 *   <ProtectedButton permission="usuarios" action="delete" variant="danger">
 *     Eliminar
 *   </ProtectedButton>
 */

export interface ProtectedButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Permiso requerido: "usuarios:create" */
  permission: string
  /** Acción separada (opcional) */
  action?: string
  /** Variante visual (por defecto "primary") */
  variant?: 'primary' | 'danger' | 'secondary' | 'ghost'
  /** Callback al hacer click (solo si tiene permiso) */
  onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void
  /** Contenido del botón */
  children: React.ReactNode
  /** Si es true, no aplica estilos inline base/variant */
  unstyled?: boolean
}

export default function ProtectedButton({
  permission,
  action,
  variant = 'primary',
  onClick,
  children,
  className,
  unstyled = false,
  ...rest
}: ProtectedButtonProps) {
  const can = usePermission()
  const getLabel = usePermissionLabel()

  const hasAccess = can(permission, action)
  const permissionLabel = getLabel(permission, action)

  const baseStyle: React.CSSProperties = {
    padding: '0.5rem 1rem',
    borderRadius: '0.375rem',
    fontSize: '0.875rem',
    fontWeight: '500',
    border: 'none',
    cursor: hasAccess ? 'pointer' : 'not-allowed',
    transition: 'all 0.2s ease',
    opacity: hasAccess ? 1 : 0.5,
  }

  const variantStyles: Record<string, React.CSSProperties> = {
    primary: {
      backgroundColor: hasAccess ? '#3b82f6' : '#9ca3af',
      color: 'white',
    },
    danger: {
      backgroundColor: hasAccess ? '#ef4444' : '#9ca3af',
      color: 'white',
    },
    secondary: {
      backgroundColor: 'white',
      color: hasAccess ? '#374151' : '#9ca3af',
      border: `1px solid ${hasAccess ? '#d1d5db' : '#e5e7eb'}`,
    },
    ghost: {
      backgroundColor: 'transparent',
      color: hasAccess ? '#3b82f6' : '#9ca3af',
    },
  }

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (!hasAccess) {
      e.preventDefault()
      return
    }
    onClick?.(e)
  }

  const mergedStyle = unstyled
    ? (rest.style as React.CSSProperties | undefined)
    : ({ ...baseStyle, ...variantStyles[variant], ...(rest.style as React.CSSProperties | undefined) } as React.CSSProperties)

  return (
    <button
      {...rest}
      disabled={!hasAccess || rest.disabled}
      onClick={handleClick}
      style={mergedStyle}
      className={className}
      title={!hasAccess ? `Permission denied: ${permissionLabel}` : ''}
    >
      {children}
    </button>
  )
}
