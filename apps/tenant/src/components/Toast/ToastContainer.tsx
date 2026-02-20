/**
 * ToastContainer - Renderiza los toasts en la esquina inferior derecha
 */
import React from 'react'
import { useToast } from './useToast'
import './toast-styles.css'

const ICONS = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'ℹ',
}

export function ToastContainer() {
  const { toasts, dismiss } = useToast()

  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`toast toast--${toast.type}`}
          role="alert"
          aria-live="polite"
        >
          <div className="toast__content">
            <span className="toast__icon">{toast.options?.icon || ICONS[toast.type]}</span>
            <span className="toast__message">{toast.message}</span>
          </div>

          {toast.options?.action && (
            <button
              className="toast__action"
              onClick={async () => {
                await toast.options.action.onClick()
                dismiss(toast.id)
              }}
            >
              {toast.options.action.label}
            </button>
          )}

          <button
            className="toast__close"
            onClick={() => dismiss(toast.id)}
            aria-label="Cerrar notificación"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}
