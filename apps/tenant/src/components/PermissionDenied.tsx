import React from 'react'
import { useTranslation } from 'react-i18next'
import { usePermissionLabel } from '../hooks/usePermissionLabel'

/**
 * PermissionDenied Component
 *
 * Muestra un mensaje de acceso denegado de forma clara y amigable.
 *
 * Uso:
 *   <PermissionDenied permission="billing:create" />
 *   <PermissionDenied permission="usuarios" action="delete" severity="error" />
 */

export interface PermissionDeniedProps {
  /** Permiso requerido */
  permission: string
  /** Acción separada (opcional) */
  action?: string
  /** Nivel de severidad (warning/error) */
  severity?: 'warning' | 'error'
  /** Mensaje personalizado (reemplaza el default) */
  message?: React.ReactNode
  /** Footer personalizado (ej: contacto al admin) */
  footer?: React.ReactNode
}

export default function PermissionDenied({
  permission,
  action,
  severity = 'error',
  message,
  footer,
}: PermissionDeniedProps) {
  const { t } = useTranslation()
  const getLabel = usePermissionLabel()

  const displayPerm = action ? `${permission}:${action}` : permission
  const label = getLabel(permission, action)

  const colors =
    severity === 'error'
      ? {
          background: '#fee2e2',
          border: '#fca5a5',
          title: '#991b1b',
          text: '#7f1d1d',
        }
      : {
          background: '#fef3c7',
          border: '#fcd34d',
          title: '#92400e',
          text: '#78350f',
        }

  return (
    <div
      style={{
        padding: '1.5rem',
        borderRadius: '0.5rem',
        backgroundColor: colors.background,
        border: `1px solid ${colors.border}`,
        margin: '1rem 0',
      }}
    >
      <h3
        style={{
          color: colors.title,
          marginBottom: '0.5rem',
          fontSize: '1.125rem',
          fontWeight: '600',
        }}
      >
        {severity === 'error' ? '❌ Unauthorized' : '⚠️ Restricted Access'}
      </h3>

      {message ? (
        <p style={{ color: colors.text, marginBottom: '0.5rem' }}>{message}</p>
      ) : (
        <>
          <p style={{ color: colors.text, marginBottom: '0.5rem' }}>
            {t('permissions.denied', {
              defaultValue: "You don't have permission for: {{action}}",
              action: label || displayPerm,
            })}
          </p>
          <p style={{ color: colors.text, fontSize: '0.875rem', marginTop: '0.25rem' }}>
            <code style={{ backgroundColor: 'rgba(0,0,0,0.1)', padding: '0.125rem 0.25rem' }}>
              {displayPerm}
            </code>
          </p>
        </>
      )}

      {footer ? (
        <div style={{ marginTop: '0.75rem', fontSize: '0.875rem', color: colors.text }}>
          {footer}
        </div>
      ) : (
        <div style={{ marginTop: '0.75rem', fontSize: '0.875rem', color: colors.text }}>
          {t('permissions.contactAdmin', {
            defaultValue: 'Contact your administrator if you believe you should have access.',
          })}
        </div>
      )}
    </div>
  )
}
