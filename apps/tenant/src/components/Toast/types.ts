/**
 * Toast System Types
 */

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface ToastAction {
  label: string
  onClick: () => void | Promise<void>
}

export interface ToastOptions {
  duration?: number // ms, 0 = no auto-dismiss
  action?: ToastAction
  icon?: React.ReactNode
}

export interface Toast {
  id: string
  type: ToastType
  message: string
  options?: ToastOptions
  timestamp: number
}

export interface ToastContextType {
  toasts: Toast[]
  success: (message: string, options?: ToastOptions) => string
  error: (message: string, options?: ToastOptions) => string
  warning: (message: string, options?: ToastOptions) => string
  info: (message: string, options?: ToastOptions) => string
  dismiss: (id: string) => void
  dismissAll: () => void
}
