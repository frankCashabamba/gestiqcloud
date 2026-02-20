/**
 * useKeyboardShortcuts - Sistema de atajos de teclado para POS
 * F2: Búsqueda | F4: Cliente | F5: Reanudar | F6: Descuento | F8: Suspender | F9: Pago
 * Enter: Confirmar | Esc: Cerrar/Volver
 */
import { useEffect } from 'react'

interface KeyboardHandlers {
  onF2?: () => void        // Buscar producto
  onF4?: () => void        // Seleccionar cliente
  onF5?: () => void        // Reanudar ticket
  onF6?: () => void        // Descuento global
  onF8?: () => void        // Suspender venta
  onF9?: () => void        // Abrir pago
  onEnter?: () => void     // Confirmar pago
  onEscape?: () => void    // Cerrar modal
  onArrowUp?: () => void   // Navegar arriba en lista
  onArrowDown?: () => void // Navegar abajo en lista
}

export function useKeyboardShortcuts(handlers: KeyboardHandlers, enabled = true) {
  useEffect(() => {
    if (!enabled) return

    const handleKeyDown = (e: KeyboardEvent) => {
      // No interceptar si estamos escribiendo en input (excepto búsqueda con F2)
      const target = e.target as HTMLElement
      const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA'
      const isContentEditable = target.contentEditable === 'true'

      // F2: Búsqueda (siempre funciona, incluso en inputs)
      if (e.code === 'F2') {
        e.preventDefault()
        handlers.onF2?.()
        return
      }

      // Si estamos en un input, solo permitir algunos atajos
      if (isInput || isContentEditable) {
        if (e.key === 'Escape') {
          handlers.onEscape?.()
        }
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
          // Ctrl+Enter en input = Confirmar
          e.preventDefault()
          handlers.onEnter?.()
        }
        return
      }

      // Resto de atajos
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
