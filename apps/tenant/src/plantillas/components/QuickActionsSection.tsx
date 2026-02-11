/**
 * QuickActionsSection
 * Componente reutilizable para acciones rápidas en dashboards
 *
 * Características:
 * - Estados disabled con tooltip
 * - Handlers validados
 * - Logging de auditoría
 * - Escalable (agregar nuevas acciones fácilmente)
 */

import React from 'react'
import type { QuickAction } from '../types/dashboard'
import { logDashboardAction } from '../services/navigationService'

interface QuickActionsSectionProps {
  actions: QuickAction[]
  title?: string
  onAction?: (actionId: string) => void
}

export const QuickActionsSection: React.FC<QuickActionsSectionProps> = ({
  actions,
  title = 'Quick actions',
  onAction,
}) => {
  const handleActionClick = (action: QuickAction) => {
    if (action.disabled) return

    // Logging
    logDashboardAction({
      action: `quick_action.${action.id}`,
      usuario: 'current_user', // Reemplazar con usuario real
      metadata: {
        label: action.label,
        module: action.requiresModule,
      },
    })

    // Ejecutar acción
    try {
      action.action()
    } catch (error) {
      console.error(`Error executing action ${action.id}:`, error)
    }

    // Callback opcional
    onAction?.(action.id)
  }

  return (
    <section className="card col-8">
      <h3>{title}</h3>
      <div className="action-grid">
        {actions.map((action) => (
          <button
            key={action.id}
            onClick={() => handleActionClick(action)}
            disabled={action.disabled}
            className="action-btn"
            title={
              action.disabled
                ? action.requiresModule
                  ? `${action.requiresModule} module required`
                  : action.requiresPermission
                  ? `Permission required: ${action.requiresPermission}`
                  : 'This action is not available'
                : action.label
            }
            style={{
              opacity: action.disabled ? 0.5 : 1,
              cursor: action.disabled ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s ease-in-out',
            }}
          >
            <span className="action-btn__icon">{action.icon}</span>
            <span>{action.label}</span>
          </button>
        ))}
      </div>

      {actions.length === 0 && (
        <div className="empty-state" style={{ padding: '20px', textAlign: 'center', color: 'var(--muted)' }}>
          No quick actions available. Enable modules to unlock actions.
        </div>
      )}
    </section>
  )
}

export default QuickActionsSection
