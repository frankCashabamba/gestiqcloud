/**
 * ToastProvider - Sistema de notificaciones no bloqueantes
 * Reemplaza alert() con toasts profesionales
 */
import React, { createContext, useCallback, useState, useId } from 'react'
import { Toast, ToastContextType, ToastType, ToastOptions } from './types'

export const ToastContext = createContext<ToastContextType | undefined>(undefined)

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = useCallback(
    (type: ToastType, message: string, options?: ToastOptions): string => {
      const id = `toast-${Date.now()}-${Math.random()}`
      const duration = options?.duration ?? (type === 'error' ? 5000 : 3000)

      const newToast: Toast = {
        id,
        type,
        message,
        options,
        timestamp: Date.now(),
      }

      setToasts((prev) => [...prev, newToast])

      // Auto-dismiss
      if (duration > 0) {
        setTimeout(() => {
          setToasts((prev) => prev.filter((t) => t.id !== id))
        }, duration)
      }

      return id
    },
    []
  )

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const dismissAll = useCallback(() => {
    setToasts([])
  }, [])

  const success = useCallback(
    (message: string, options?: ToastOptions) => addToast('success', message, options),
    [addToast]
  )

  const error = useCallback(
    (message: string, options?: ToastOptions) => addToast('error', message, options),
    [addToast]
  )

  const warning = useCallback(
    (message: string, options?: ToastOptions) => addToast('warning', message, options),
    [addToast]
  )

  const info = useCallback(
    (message: string, options?: ToastOptions) => addToast('info', message, options),
    [addToast]
  )

  const value: ToastContextType = {
    toasts,
    success,
    error,
    warning,
    info,
    dismiss,
    dismissAll,
  }

  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>
}
