/**
 * useKeyboardShortcuts - Sistema de atajos de teclado para POS
 * F1: Nuevo pedido | F2: Búsqueda | F4: Cliente | F5: Reanudar | F6: Descuento | F7: Proforma
 * F8: Suspender | F9: Pago | F10: Cobro express (sin ticket) | F11: Cobro express (con ticket)
 * Enter: Confirmar | Esc: Cerrar/Volver
 */
import { useEffect } from 'react'

interface KeyboardHandlers {
  onF1?: () => void
  onF2?: () => void
  onF4?: () => void
  onF5?: () => void
  onF6?: () => void
  onF7?: () => void
  onF8?: () => void
  onF9?: () => void
  onF10?: () => void
  onF11?: () => void
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

      if (e.code === 'F1') {
        e.preventDefault()
        handlers.onF1?.()
        return
      }

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
        case 'F7':
          e.preventDefault()
          handlers.onF7?.()
          break
        case 'F8':
          e.preventDefault()
          handlers.onF8?.()
          break
        case 'F9':
          e.preventDefault()
          handlers.onF9?.()
          break
        case 'F10':
          e.preventDefault()
          handlers.onF10?.()
          break
        case 'F11':
          e.preventDefault()
          handlers.onF11?.()
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

    // useCapture=true intercepta antes de que el browser procese F10/F11/etc.
    window.addEventListener('keydown', handleKeyDown, true)
    return () => window.removeEventListener('keydown', handleKeyDown, true)
  }, [handlers, enabled])
}
