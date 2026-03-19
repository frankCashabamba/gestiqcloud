/**
 * useKeyboardShortcuts - Sistema de atajos de teclado para POS
 * F2: BÃºsqueda | F4: Cliente | F5: Reanudar | F6: Descuento | F8: Suspender | F9: Pago
 * Enter: Confirmar | Esc: Cerrar/Volver
 */
import { useEffect } from 'react'

interface KeyboardHandlers {
  onF2?: () => void
  onF4?: () => void
  onF5?: () => void
  onF6?: () => void
  onF8?: () => void
  onF9?: () => void
  onEnter?: () => void
  onEscape?: () => void
  onArrowUp?: () => void
  onArrowDown?: () => void
}

export function useKeyboardShortcuts(handlers: KeyboardHandlers, enabled = true) {
  useEffect(() => {
    if (!enabled) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.defaultPrevented) return

      const target = e.target as HTMLElement
      const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA'
      const isContentEditable = target.contentEditable === 'true'

      if (e.code === 'F2') {
        e.preventDefault()
        handlers.onF2?.()
        return
      }

      if (isInput || isContentEditable) {
        if (e.key === 'Escape') {
          handlers.onEscape?.()
        }
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
          e.preventDefault()
          handlers.onEnter?.()
        }
        return
      }

      switch (e.code) {
        case 'F4':
          e.preventDefault()
          handlers.onF4?.()
          break
        case 'F5':
          e.preventDefault()
          handlers.onF5?.()
          break
        case 'F6':
          e.preventDefault()
          handlers.onF6?.()
          break
        case 'F8':
          e.preventDefault()
          handlers.onF8?.()
          break
        case 'F9':
          e.preventDefault()
          handlers.onF9?.()
          break
        case 'Enter':
          e.preventDefault()
          handlers.onEnter?.()
          break
        case 'Escape':
          handlers.onEscape?.()
          break
        case 'ArrowUp':
          e.preventDefault()
          handlers.onArrowUp?.()
          break
        case 'ArrowDown':
          e.preventDefault()
          handlers.onArrowDown?.()
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handlers, enabled])
}
