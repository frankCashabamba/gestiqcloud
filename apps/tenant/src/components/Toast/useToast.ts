/**
 * useToast - Hook para acceder al sistema de toasts
 */
import { useContext } from 'react'
import { ToastContext } from './ToastProvider'
import { ToastContextType } from './types'

export function useToast(): ToastContextType {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within ToastProvider')
  }
  return context
}
